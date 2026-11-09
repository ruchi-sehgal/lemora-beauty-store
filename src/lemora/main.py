from fastapi import FastAPI

app= FastAPI(title="Lemora Beauty Store")
@app.get("/health")
def health():
    return {"status": "ok"}