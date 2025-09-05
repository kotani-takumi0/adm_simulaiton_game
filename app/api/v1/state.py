# app/api/v1/state.py
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.config import settings


router = APIRouter()
_SESSIONS: dict[str, dict] = {}

class StartResponse(BaseModel):
    session_id: str
    year: int
    year_budget_total: float
    year_budget_remaining: float
    scheduled_event_ids: list[str]
    currency: str = "JPY"  # 明示的に返すと誤解が減る

@router.post("/start", response_model=StartResponse)
def start():
    """サーバ側で決めた設定（5年・12件/年・1500億/年）でセッションを開始。"""
    years = settings.GAME_YEARS
    events_per_year = settings.GAME_EVENTS_PER_YEAR
    budget_per_year = settings.GAME_BUDGET_PER_YEAR

    # 初年度の予定（ダミーID）。後で実データに差し替え
    scheduled = {1: [f"E{i:03d}" for i in range(1, events_per_year + 1)]}

    session_id = str(uuid.uuid4())
    _SESSIONS[session_id] = {
        "year": 1,
        "years_total": years,
        "year_budget_total": budget_per_year,
        "year_budget_remaining": budget_per_year,
        "events_per_year": events_per_year,           # ← 次年度遷移でも使う
        "schedule": scheduled,                        # {year: [event_id,...]}
        "done_events": set(),
        "allocations": {},
        "predictions": {},
        "scores": {},
    }

    return StartResponse(
        session_id=session_id,
        year=1,
        year_budget_total=budget_per_year,
        year_budget_remaining=budget_per_year,
        scheduled_event_ids=scheduled[1],
        currency=settings.GAME_CURRENCY,
    )


# app/api/v1/state.py に追記
from fastapi import Body
from pydantic import BaseModel

class NextYearResponse(BaseModel):
    moved_to_year: int
    year_budget_total: float
    year_budget_remaining: float

@router.post("/next_year", response_model=NextYearResponse)
def next_year(session_id: str = Body(..., embed=True)):
    session = _SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")

    year = session["year"]
    # まだ残っていれば進めない
    if session["schedule"].get(year, []):
        raise HTTPException(status_code=409, detail="events remain in this year")

    # 最終年度は進めない
    if year >= session["years_total"]:
        raise HTTPException(status_code=409, detail="already at final year")

    # 年+1、予算リセット、次年度の12件を補充
    next_year = year + 1
    session["year"] = next_year
    session["year_budget_remaining"] = session["year_budget_total"]
    events_per_year = session["events_per_year"]
    session["schedule"][next_year] = [f"E{i:03d}" for i in range(1, events_per_year + 1)]

    return NextYearResponse(
        moved_to_year=next_year,
        year_budget_total=session["year_budget_total"],
        year_budget_remaining=session["year_budget_remaining"],
    )
