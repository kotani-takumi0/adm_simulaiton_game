# app/api/v1/state.py
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

# MVP：起動中だけ生きる簡易KVS（あとでRedis等に差し替え可）
_SESSIONS: dict[str, dict] = {}

class StartRequest(BaseModel):
    years: int = Field(ge=1, le=10, default=3)  # 複数学年を回す
    budget_per_year: float = Field(gt=0, default=150_000_000_000)
    events_per_year: int = Field(ge=1, le=60, default=10)
    shuffle_seed: int = 42  # 後で乱択に使う

@router.post("/start")
def start(req: StartRequest):
    """
    セッションを開始し、当年のスケジュールと予算の初期値を返す。
    今はダミーのイベントIDを並べ、後で実データ60件から抽選に差し替え。
    """
    # 当年に提示するイベント（今は E001.. のダミー）
    scheduled = {1: [f"E{i:03d}" for i in range(1, req.events_per_year + 1)]}

    session_id = str(uuid.uuid4())
    _SESSIONS[session_id] = {
        "year": 1,
        "years_total": req.years,
        "year_budget_total": req.budget_per_year,
        "year_budget_remaining": req.budget_per_year,
        "schedule": scheduled,      # {year: [event_id,...]}
        "done_events": set(),       # 進行済みイベント
        "allocations": {},          # event_id -> allocated_budget
        "predictions": {},          # event_id -> predicted_init_budget
        "scores": {},               # event_id -> score
    }

    return {
        "session_id": session_id,
        "year": 1,
        "year_budget_total": req.budget_per_year,
        "year_budget_remaining": req.budget_per_year,
        "scheduled_event_ids": scheduled[1],
    }
