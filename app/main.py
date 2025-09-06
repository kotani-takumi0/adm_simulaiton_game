# app/main.py
from fastapi import FastAPI
from fastapi.responses import RedirectResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.state import router as state_router
from app.api.v1.events import router as events_router
from app.api.v1.budget import router as budget_router
from app.core.config import settings
from app.api.v1.metrics import router as metrics_router
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Policy Game API", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok"}

# Redirect root to UI
@app.get("/")
def root_redirect():
    return RedirectResponse(url="/ui/")

# Avoid noisy 404 for browsers requesting a favicon
@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)

# /v1/state/... のルート群を登録
app.include_router(state_router, prefix="/v1/state", tags=["state"])
app.include_router(events_router, prefix="/v1/events", tags=["events"])
app.include_router(budget_router, prefix="/v1", tags=["budget"])
app.include_router(metrics_router, prefix="/v1/metrics", tags=["metrics"])

# CORS
_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static UI (simple test frontend)
app.mount("/ui", StaticFiles(directory="web", html=True), name="ui")
