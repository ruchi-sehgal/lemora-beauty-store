import hashlib
import time

import httpx

from lemora.db import query
from lemora.embeddings import DIMS, MODEL, embed_documents, to_pgvector

BATCH = 50


def product_text(p):
    parts = [f"{p['brand']} {p['name']}", f"{p['category']} / {p['product_type']}"]
    for label, key in [("Fragrance family", "fragrance_family"), ("Benefit", "benefit"),
                       ("Key ingredients", "key_ingredients"), ("Notes", "fragrance_notes"),
                       ("Audience", "target_audience"), ("Gender", "gender")]:
        if p.get(key):
            parts.append(f"{label}: {p[key]}")
    if p["skin_types"]:
        parts.append("Skin types: " + ", ".join(p["skin_types"]))
    if p["concerns"]:
        parts.append("Concerns: " + ", ".join(p["concerns"]))
    return ". ".join(parts)          # note: no price, so a price change never makes a vector stale


def fingerprint(text):
    return hashlib.sha256(f"{MODEL}|{DIMS}|{text}".encode()).hexdigest()


def run():
    started = time.perf_counter()
    rows = query(
        "SELECT sku_id, brand, name, category, product_type, fragrance_family, benefit, "
        "key_ingredients, fragrance_notes, target_audience, gender, skin_types, concerns, "
        "content_hash, (embedding IS NULL) AS no_vector FROM products WHERE is_active"
    )
    todo = []
    for p in rows:
        text = product_text(p)
        h = fingerprint(text)
        if p["no_vector"] or p["content_hash"] != h:
            todo.append((p["sku_id"], text, h))

    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        try:
            vectors = embed_documents([t for _, t, _ in chunk])
        except httpx.HTTPStatusError:
            time.sleep(60)               # free-tier limit hit: wait a minute, try once more
            vectors = embed_documents([t for _, t, _ in chunk])
        for (sku, _, h), vec in zip(chunk, vectors):
            query(
                "UPDATE products SET embedding = %(e)s::vector, content_hash = %(h)s, "
                "embedding_model = %(m)s, embedded_at = now() WHERE sku_id = %(s)s RETURNING sku_id",
                {"e": to_pgvector(vec), "h": h, "m": MODEL, "s": sku},
            )
        print(f"embedded {min(i + BATCH, len(todo))}/{len(todo)}")
        if i + BATCH < len(todo):
            time.sleep(15)

    seconds = time.perf_counter() - started
    print(f"done: embedded {len(todo)}, already fresh {len(rows) - len(todo)}, took {seconds:.1f}s")


if __name__ == "__main__":
    run()