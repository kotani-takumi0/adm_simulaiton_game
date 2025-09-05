# app/api/v1/state.py
import uuid
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from app.core.config import settings
from typing import List, Optional
from app.services.events_catalog import get_all_event_ids, get_event_meta


router = APIRouter()
_SESSIONS: dict[str, dict] = {}

class StartRequest(BaseModel):
    # 任意: 初年度に提示するイベントIDを指定（最大 events_per_year 件）
    event_ids: Optional[List[str]] = None


class StartResponse(BaseModel):
    session_id: str
    year: int
    year_budget_total: float
    year_budget_remaining: float
    scheduled_event_ids: list[str]
    currency: str = "JPY"  # 明示的に返すと誤解が減る
    # 選定イベントの簡易メタ（事業名・現状・課題）
    events_meta: list[dict] | None = None

@router.post("/start", response_model=StartResponse)
def start(req: StartRequest | None = Body(default=None)):
    """サーバ側で決めた設定（5年・12件/年・1500億/年）でセッションを開始。"""
    years = settings.GAME_YEARS
    events_per_year = settings.GAME_EVENTS_PER_YEAR
    budget_per_year = settings.GAME_BUDGET_PER_YEAR

    # 実データからイベントIDを採番（リクエストで指定があれば優先）
    all_ids = get_all_event_ids()
    if req and req.event_ids:
        # 指定されたIDのうち存在するもののみ採用、先頭から events_per_year 件まで
        id_set = set(map(str, all_ids))
        filtered = [str(e) for e in req.event_ids if str(e) in id_set]
        scheduled_ids = filtered[:events_per_year]
    else:
        scheduled_ids = [str(eid) for eid in all_ids[:events_per_year]]
    scheduled = {1: scheduled_ids}

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

    # 事業名と現状・課題を抽出
    metas: list[dict] = []
    for eid in scheduled_ids:
        try:
            meta = get_event_meta(eid)
            metas.append({
                "予算事業ID": str(eid),
                "事業名": meta.get("事業名"),
                "現状・課題": meta.get("現状・課題"),
            })
        except Exception:
            metas.append({"予算事業ID": str(eid)})

    return StartResponse(
        session_id=session_id,
        year=1,
        year_budget_total=budget_per_year,
        year_budget_remaining=budget_per_year,
        scheduled_event_ids=scheduled[1],
        currency=settings.GAME_CURRENCY,
        events_meta=metas,
    )


# app/api/v1/state.py に追記

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

    # 年+1、予算リセット、次年度の events_per_year 件を補充（selected_game.csv の順にスライス）
    next_year = year + 1
    session["year"] = next_year
    session["year_budget_remaining"] = session["year_budget_total"]
    events_per_year = session["events_per_year"]
    all_ids = get_all_event_ids()
    start_idx = (next_year - 1) * events_per_year
    end_idx = start_idx + events_per_year
    next_ids = [str(eid) for eid in all_ids[start_idx:end_idx]]
    if not next_ids:
        # データが尽きた場合、空のままにしておきクライアント側で処理
        next_ids = []
    session["schedule"][next_year] = next_ids

    return NextYearResponse(
        moved_to_year=next_year,
        year_budget_total=session["year_budget_total"],
        year_budget_remaining=session["year_budget_remaining"],
    )
