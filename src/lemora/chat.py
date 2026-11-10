import os
import uuid
import time

from lemora.agent import agent
from lemora.db import query

PROMPT_VERSION = "v1"
HISTORY_MESSAGES = 10


def start_conversation(visitor_id):
    rows = query(
        "INSERT INTO conversations (visitor_id) VALUES (%(v)s) RETURNING conversation_id",
        {"v": visitor_id},
    )
    return str(rows[0]["conversation_id"])


def load_history(conversation_id):
    rows = query(
        "SELECT role, content, recommended_skus FROM messages "
        "WHERE conversation_id = %(c)s ORDER BY message_id DESC LIMIT %(n)s",
        {"c": conversation_id, "n": HISTORY_MESSAGES},
    )
    return list(reversed(rows))


def build_prompt(history, message):
    if not history:
        return message
    lines = []
    for m in history:
        who = "Shopper" if m["role"] == "user" else "Assistant"
        shown = f" [recommended: {', '.join(m['recommended_skus'])}]" if m["recommended_skus"] else ""
        lines.append(f"{who}: {m['content']}{shown}")
    return "Conversation so far:\n" + "\n".join(lines) + f"\n\nNew shopper message: {message}"


def save_message(conversation_id, role, content, skus=None, latency_ms=None):
    is_assistant = role == "assistant"
    rows = query(
        "INSERT INTO messages (conversation_id, role, content, recommended_skus, "
        "prompt_version, model, latency_ms) "
        "VALUES (%(c)s, %(role)s, %(content)s, %(skus)s, %(pv)s, %(model)s, %(ms)s) "
        "RETURNING message_id",
        {
            "c": conversation_id, "role": role, "content": content, "skus": skus or [],
            "pv": PROMPT_VERSION if is_assistant else None,
            "model": os.environ["GROQ_MODEL"] if is_assistant else None,
            "ms": latency_ms,
        },
    )
    return rows[0]["message_id"]


def cards_for(skus):
    if not skus:
        return []
    rows = query(
        "SELECT sku_id, brand, name, category, price_sgd FROM products "
        "WHERE is_active AND sku_id = ANY(%(s)s::text[])",
        {"s": skus},
    )
    by_id = {r["sku_id"]: {**r, "price_sgd": float(r["price_sgd"])} for r in rows}
    return [by_id[s] for s in skus if s in by_id]


def chat(conversation_id, message):
    history = load_history(conversation_id)
    started = time.perf_counter()
    reply = agent.run_sync(build_prompt(history, message)).output
    latency_ms = int((time.perf_counter() - started) * 1000)

    cards = cards_for([r.sku_id for r in reply.recommendations])
    save_message(conversation_id, "user", message)
    message_id = save_message(
        conversation_id, "assistant", reply.message, [c["sku_id"] for c in cards], latency_ms
    )
    return {
        "message_id": message_id,
        "message": reply.message,
        "products": cards,
        "follow_up_question": reply.follow_up_question,
    }


def owns_conversation(conversation_id, visitor_id):
    try:
        uuid.UUID(conversation_id)
    except ValueError:
        return False
    rows = query(
        "SELECT 1 FROM conversations WHERE conversation_id = %(c)s AND visitor_id = %(v)s",
        {"c": conversation_id, "v": visitor_id},
    )
    return bool(rows)