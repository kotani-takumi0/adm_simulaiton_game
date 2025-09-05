# app/main.py
from fastapi import FastAPI
from app.api.v1.state import router as state_router

app = FastAPI(title="Policy Game API", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok"}

# /v1/state/... のルート群を登録
app.include_router(state_router, prefix="/v1/state", tags=["state"])
