from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates

from lemora.db import query

app = FastAPI(title="Lemora Beauty Store")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


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
    return templates.TemplateResponse(request, "product.html", {"p": rows[0]})