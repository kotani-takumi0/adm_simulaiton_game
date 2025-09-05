# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.state import router as state_router
from app.api.v1.events import router as events_router
from app.api.v1.budget import router as budget_router
from app.core.config import settings

app = FastAPI(title="Policy Game API", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok"}

# /v1/state/... のルート群を登録
app.include_router(state_router, prefix="/v1/state", tags=["state"])
app.include_router(events_router, prefix="/v1/events", tags=["events"])
app.include_router(budget_router, prefix="/v1", tags=["budget"])

# CORS
_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
