import os

import httpx

MODEL = "gemini-embedding-001"
DIMS = 768
BASE = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}"


def _headers():
    return {"x-goog-api-key": os.environ["GEMINI_API_KEY"]}


def embed_query(text):
    """Meaning-numbers for a shopper's search wording."""
    r = httpx.post(
        f"{BASE}:embedContent", headers=_headers(), timeout=20,
        json={"content": {"parts": [{"text": text}]},
              "taskType": "RETRIEVAL_QUERY", "outputDimensionality": DIMS},
    )
    r.raise_for_status()
    return r.json()["embedding"]["values"]


def embed_documents(texts):
    """Meaning-numbers for product descriptions (a batch at a time)."""
    body = {"requests": [
        {"model": f"models/{MODEL}", "content": {"parts": [{"text": t}]},
         "taskType": "RETRIEVAL_DOCUMENT", "outputDimensionality": DIMS}
        for t in texts
    ]}
    r = httpx.post(f"{BASE}:batchEmbedContents", headers=_headers(), timeout=90, json=body)
    r.raise_for_status()
    return [e["values"] for e in r.json()["embeddings"]]


def to_pgvector(values):
    return "[" + ",".join(str(v) for v in values) + "]"