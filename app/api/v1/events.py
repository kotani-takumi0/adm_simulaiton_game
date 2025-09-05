# app/api/v1/events.py
from fastapi import APIRouter, HTTPException, Query
from app.api.v1.state import _SESSIONS  # MVP: stateが持つKVSを使い回す
from app.services.events_catalog import get_event_meta, get_all_event_ids
from pydantic import BaseModel, Field, ConfigDict

router = APIRouter()

@router.get("/next")
def next_event(session_id: str = Query(..., description="start()で得たUUID")):
    """
    当年の未提示イベントから1件取り出して返す。
    - 予定キュー(schedule[year])の先頭をpop
    - 残件数を返却
    """
    session = _SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")

    year = session["year"]
    schedule = session["schedule"].get(year, [])
    if not schedule:
        # 予定が空：年度のイベントを出し切った
        # クライアントは /v1/state/next_year を呼んで遷移する想定
        raise HTTPException(status_code=409, detail="no remaining events in this year")

    event_id = schedule.pop(0)  # 先頭を取り出す（重複防止）
    remaining = len(schedule)

    # メタ情報の付与（selected_game.csv 由来）
    try:
        meta = get_event_meta(event_id)
    except Exception:
        meta = {"予算事業ID": event_id}

    return {
        "year": year,
        "予算事業ID": event_id,
        "remaining_in_year": remaining,
        "meta": meta,
    }


# 任意のIDからメタを取得する簡易API
class EventMetaResponse(BaseModel):
    # Use ASCII attribute names with Japanese aliases for validation/serialization
    yosan_jigyo_id: str | None = Field(None, validation_alias="予算事業ID", serialization_alias="予算事業ID")
    jigyo_mei: str | None = Field(None, validation_alias="事業名", serialization_alias="事業名")
    jigyo_no_gaiyo: str | None = Field(None, validation_alias="事業の概要", serialization_alias="事業の概要")
    genjo_kadai: str | None = Field(None, validation_alias="現状・課題", serialization_alias="現状・課題")
    tosho_yosan: float | None = Field(None, validation_alias="当初予算", serialization_alias="当初予算")
    saishutsu_yosan_genkaku: float | None = Field(None, validation_alias="歳出予算現額", serialization_alias="歳出予算現額")

    model_config = ConfigDict(populate_by_name=True)


@router.get("/meta", response_model=EventMetaResponse)
def event_meta(budget_id: str = Query(..., description="selected_game.csv の 予算事業ID")):
    try:
        return get_event_meta(budget_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="budget_id not found")


@router.get("/overview", response_model=EventMetaResponse)
def event_overview():
    """Return the default overview item picked from selected_game.csv.
    Currently selects the first row's 予算事業ID.
    """
    ids = get_all_event_ids()
    if not ids:
        raise HTTPException(status_code=404, detail="no events available")
    try:
        return get_event_meta(str(ids[0]))
    except KeyError:
        raise HTTPException(status_code=404, detail="default event not found")


@router.get("/ids", response_model=list[str])
def event_ids():
    """Return all available event ids from selected_game.csv as strings."""
    ids = [str(i) for i in get_all_event_ids()]
    if not ids:
        raise HTTPException(status_code=404, detail="no events available")
    return ids
