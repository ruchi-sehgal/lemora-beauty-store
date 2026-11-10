import os
import time
import uuid

from pydantic_ai.usage import UsageLimits

from lemora.agent import ChatDeps, agent
from lemora.db import query
from lemora.guardrails import scrub_pii

PROMPT_VERSION = "v5"
HISTORY_MESSAGES = 6


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


def save_message(conversation_id, role, content, skus=None, latency_ms=None, usage=None):
    is_assistant = role == "assistant"
    rows = query(
        "INSERT INTO messages (conversation_id, role, content, recommended_skus, "
        "prompt_version, model, latency_ms, input_tokens, output_tokens, model_requests) "
        "VALUES (%(c)s, %(role)s, %(content)s, %(skus)s, %(pv)s, %(model)s, %(ms)s, "
        "%(tin)s, %(tout)s, %(req)s) RETURNING message_id",
        {
            "c": conversation_id, "role": role, "content": content, "skus": skus or [],
            "pv": PROMPT_VERSION if is_assistant else None,
            "model": os.environ["GROQ_MODEL"] if is_assistant else None,
            "ms": latency_ms,
            "tin": usage.input_tokens if usage else None,
            "tout": usage.output_tokens if usage else None,
            "req": usage.requests if usage else None,
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


def shown_skus(conversation_id):
    rows = query(
        "SELECT DISTINCT unnest(recommended_skus) AS sku FROM messages "
        "WHERE conversation_id = %(c)s",
        {"c": conversation_id},
    )
    return [r["sku"] for r in rows]


def chat(conversation_id, message):
    message, pii_found = scrub_pii(message)
    history = load_history(conversation_id)
    started = time.perf_counter()
    result = agent.run_sync(
        build_prompt(history, message),
        deps=ChatDeps(conversation_id=conversation_id, shown_skus=shown_skus(conversation_id)),
        usage_limits=UsageLimits(request_limit=6, tool_calls_limit=3),
    )
    reply = result.output
    usage = result.usage()
    latency_ms = int((time.perf_counter() - started) * 1000)

    text = reply.message
    if pii_found:
        text += " (For your privacy, I removed personal details from your message.)"

    cards = cards_for([r.sku_id for r in reply.recommendations][:4])
    save_message(conversation_id, "user", message)
    message_id = save_message(
        conversation_id, "assistant", text, [c["sku_id"] for c in cards], latency_ms, usage
    )
    return {
        "message_id": message_id,
        "message": text,
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


def history_for_widget(conversation_id, limit=30):
    rows = query(
        "SELECT message_id, role, content, recommended_skus FROM messages "
        "WHERE conversation_id = %(c)s ORDER BY message_id DESC LIMIT %(n)s",
        {"c": conversation_id, "n": limit},
    )
    return [
        {
            "message_id": r["message_id"],
            "role": r["role"],
            "message": r["content"],
            "products": cards_for(r["recommended_skus"] or []),
        }
        for r in reversed(rows)
    ]