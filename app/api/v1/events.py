# app/api/v1/events.py
from fastapi import APIRouter, HTTPException, Query
from app.api.v1.state import _SESSIONS  # MVP: stateが持つKVSを使い回す

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

    return {
        "year": year,
        "event_id": event_id,
        # 本番ではここに purpose_needs やメタ情報を追加する
        "remaining_in_year": remaining
    }
