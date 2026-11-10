import hmac
import os
import uuid
import zlib
from pathlib import Path
from typing import Literal


from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from lemora.chat import chat, history_for_widget, owns_conversation, start_conversation
from lemora.db import query
from lemora.guardrails import allow, looks_like_injection
from lemora.metrics import collect
from lemora.observability import setup

HERE = Path(__file__).parent
setup()
app = FastAPI(title="Lemora Beauty Store")
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
templates = Jinja2Templates(directory=HERE / "templates")


def hue_for(brand):
    return zlib.crc32(brand.encode()) % 360

def log_event(kind, detail=""):
    try:
        query(
            "INSERT INTO error_log (kind, detail) VALUES (%(k)s, %(d)s) RETURNING error_id",
            {"k": kind, "d": detail[:500]},
        )
    except Exception as error:                      # logging must never break the chat
        print("could not log event:", repr(error))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def home(request: Request, category: str = "", brand: str = "", max_price: str = ""):
    try:
        limit = float(max_price) if max_price.strip() else None
    except ValueError:
        limit = None

    products = query(
        "SELECT sku_id, brand, name, category, price_sgd FROM products "
        "WHERE is_active "
        "AND (%(category)s = '' OR category = %(category)s) "
        "AND (%(brand)s = '' OR brand = %(brand)s) "
        "AND (%(limit)s::numeric IS NULL OR price_sgd <= %(limit)s::numeric) "
        "ORDER BY brand, name",
        {"category": category, "brand": brand, "limit": limit},
    )
    for p in products:
        p["hue"] = hue_for(p["brand"])
    brands = [r["brand"] for r in query(
        "SELECT DISTINCT brand FROM products WHERE is_active ORDER BY brand")]
    categories = [r["category"] for r in query(
        "SELECT DISTINCT category FROM products WHERE is_active ORDER BY category")]

    return templates.TemplateResponse(request, "index.html", {
        "products": products, "brands": brands, "categories": categories,
        "category": category, "brand": brand, "max_price": max_price,
    })


@app.get("/product/{sku_id}")
def product(request: Request, sku_id: str):
    rows = query(
        "SELECT * FROM products WHERE sku_id = %(sku_id)s AND is_active",
        {"sku_id": sku_id},
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Product not found")
    p = rows[0]
    p["hue"] = hue_for(p["brand"])
    return templates.TemplateResponse(request, "product.html", {"p": p})


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    conversation_id: str | None = None


@app.post("/api/chat")
def api_chat(body: ChatIn, request: Request):
    visitor_id = request.cookies.get("visitor_id") or uuid.uuid4().hex
    client_ip = request.client.host if request.client else "unknown"
    if not allow("visitor:" + visitor_id, limit=20) or not allow("ip:" + client_ip, limit=60):
        log_event("rate_limited")
        return JSONResponse(
            {"message": "You're sending messages very quickly. Please wait a few minutes and try again."},
            status_code=429,
        )
    if looks_like_injection(body.message):
        log_event("injection_blocked")
        return JSONResponse(
            {"message": "I can only help with Lemora beauty products. What are you looking for today?"},
            status_code=400,
        )
    conversation_id = body.conversation_id
    if not conversation_id or not owns_conversation(conversation_id, visitor_id):
        conversation_id = start_conversation(visitor_id)

    try:
        result = chat(conversation_id, body.message)
    except Exception as error:
        print("chat failed:", repr(error))
        log_event("chat_failed", repr(error))
        return JSONResponse(
            {"fallback": True, "message": "The assistant is unavailable right now. "
             "You can still browse the store with the filters."},
            status_code=503,
        )

    response = JSONResponse({**result, "conversation_id": conversation_id})
    response.set_cookie("visitor_id", visitor_id, max_age=60 * 60 * 24 * 90,
                        httponly=True, samesite="lax",
                        secure=os.environ.get("COOKIE_SECURE") == "1")
    return response


class FeedbackIn(BaseModel):
    message_id: int
    verdict: Literal["accepted", "corrected", "rejected"] | None = None
    correction_text: str | None = Field(default=None, max_length=500)
    csat_score: int | None = Field(default=None, ge=1, le=5)


@app.post("/api/feedback")
def api_feedback(body: FeedbackIn, request: Request):
    if body.verdict is None and body.csat_score is None:
        raise HTTPException(status_code=422, detail="Send a verdict or a rating")
    visitor_id = request.cookies.get("visitor_id")
    mine = query(
        """
        SELECT 1 FROM messages m
        JOIN conversations c USING (conversation_id)
        WHERE m.message_id = %(m)s AND m.role = 'assistant' AND c.visitor_id = %(v)s
        """,
        {"m": body.message_id, "v": visitor_id},
    )
    if not mine:
        raise HTTPException(status_code=404, detail="Message not found")

    query(
        """
        INSERT INTO feedback (message_id, verdict, correction_text, csat_score)
        VALUES (%(m)s, %(verdict)s, %(text)s, %(score)s)
        RETURNING feedback_id
        """,
        {"m": body.message_id, "verdict": body.verdict,
         "text": body.correction_text, "score": body.csat_score},
    )
    return {"ok": True}


@app.get("/api/history")
def api_history(conversation_id: str, request: Request):
    visitor_id = request.cookies.get("visitor_id")
    if not visitor_id or not owns_conversation(conversation_id, visitor_id):
        return {"messages": []}
    return {"messages": history_for_widget(conversation_id)}


@app.get("/admin/metrics")
def admin_metrics(request: Request, key: str = ""):
    expected = os.environ.get("ADMIN_KEY", "")
    if not expected or not hmac.compare_digest(key, expected):
        raise HTTPException(status_code=404)        # pretend the page doesn't exist
    return templates.TemplateResponse(request, "metrics.html", {"m": collect()})