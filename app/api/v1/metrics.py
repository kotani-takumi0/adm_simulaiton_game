from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
import math

from app.api.v1.state import _SESSIONS
from app.services.events_catalog import get_event_meta
from app.services.datastore import load_budget_data
from app.services.embedding import embed_text_to_vec
from app.services.predictor import predict_initial_budget


router = APIRouter()


class MonthMetric(BaseModel):
    month: int
    event_id: Optional[str] = None
    name: Optional[str] = None
    actual_initial: Optional[float] = None
    allocated: Optional[float] = None
    tolerance_low: Optional[float] = None
    tolerance_high: Optional[float] = None
    ai_reference: Optional[float] = None
    within_tolerance: Optional[bool] = None


class YearMetrics(BaseModel):
    session_id: str
    year: int
    months: List[MonthMetric]


@router.get("/months", response_model=YearMetrics)
def months_metrics(session_id: str = Query(..., description="start()で得たUUID")):
    session = _SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")

    year = int(session.get("year", 1))
    events_per_year = int(session.get("events_per_year", 12))
    timeline = session.get("timeline", {}).get(year, [])

    # 予測のための埋め込み次元を一度だけ取得
    try:
        data = load_budget_data()
        x_dim = int(data.X1.shape[1])
    except Exception:
        data = None
        x_dim = None

    months: list[MonthMetric] = []
    max_len = min(events_per_year, len(timeline)) if timeline else events_per_year

    for i in range(max_len):
        month_no = i + 1
        eid = str(timeline[i]) if i < len(timeline) else None
        name = None
        actual = None
        allocated = None
        tol_low = None
        tol_high = None
        ai_ref = None
        within = None

        if eid:
            try:
                meta = get_event_meta(eid)
                name = meta.get("事業名")
                v = meta.get("当初予算")
                if v is not None:
                    try:
                        fv = float(v)
                        if math.isfinite(fv):
                            actual = fv
                            tol_low = fv * 0.8
                            tol_high = fv * 1.2
                    except Exception:
                        pass
                allocated = session.get("allocations", {}).get(eid)
                if allocated is not None:
                    try:
                        af = float(allocated)
                        if math.isfinite(af) and actual is not None:
                            within = (tol_low <= af <= tol_high) if (tol_low is not None and tol_high is not None) else None
                        allocated = af
                    except Exception:
                        pass
                # AI参考値（課題 or 概要を入力として推定）
                if x_dim is not None and data is not None:
                    text = meta.get("現状・課題") or meta.get("事業の概要") or None
                    if text and isinstance(text, str) and text.strip():
                        try:
                            q = embed_text_to_vec(text, dim=x_dim, normalize=True)
                            pr = predict_initial_budget(q)
                            if pr and pr.get("can_estimate"):
                                ev = float(pr.get("estimate_initial"))
                                if math.isfinite(ev):
                                    ai_ref = ev
                        except Exception:
                            ai_ref = None
            except Exception:
                pass

        months.append(MonthMetric(
            month=month_no,
            event_id=eid,
            name=name,
            actual_initial=actual,
            allocated=allocated,
            tolerance_low=tol_low,
            tolerance_high=tol_high,
            ai_reference=ai_ref,
            within_tolerance=within,
        ))

    return YearMetrics(session_id=session_id, year=year, months=months)

