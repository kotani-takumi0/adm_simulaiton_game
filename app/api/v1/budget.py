# app/api/v1/budget.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import numpy as np

from app.api.v1.state import _SESSIONS  # MVP: セッションKVSを共用
from app.services.predictor import predict_initial_budget

router = APIRouter()

# ========== 1) 予算割当 (/v1/allocate) ==========

class AllocateRequest(BaseModel):
    session_id: str
    event_id: str
    allocated_budget: float = Field(gt=0, description="円。0は不可")

class AllocateResponse(BaseModel):
    year: int
    year_budget_remaining: float
    allocation_saved: bool = True

@router.post("/allocate", response_model=AllocateResponse)
def allocate(req: AllocateRequest):
    """
    予算割当：
    - session存在チェック（なければ404）
    - 残額 < 割当なら422
    - OKなら allocations[event_id] に保存し、残額を減算
    """
    session = _SESSIONS.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")

    # 既存割当との差分のみを残額に反映（上書き動作）
    remaining = float(session["year_budget_remaining"])
    prev = float(session["allocations"].get(req.event_id, 0.0))
    new = float(req.allocated_budget)
    delta = new - prev  # 追加で必要な増分（マイナスなら残額が戻る）

    if delta > remaining:
        over = delta - remaining
        raise HTTPException(status_code=422, detail=f"budget exceeded by {over:.0f} JPY (delta)")

    # 保存＆残額更新（上書きで整合）
    session["allocations"][req.event_id] = new
    session["year_budget_remaining"] = remaining - delta

    return AllocateResponse(
        year=session["year"],
        year_budget_remaining=float(session["year_budget_remaining"]),
        allocation_saved=True,
    )

# ========== 2) 予算推定 (/v1/budget/predict) ==========

class PredictRequest(BaseModel):
    # MVP: 埋め込みを直接受ける（後でテキスト→埋め込みへ置換）
    query_vec_1: list[float] = Field(..., min_length=1)
    query_vec_2: list[float] | None = Field(default=None, min_length=1)

class PredictResponse(BaseModel):
    can_estimate: bool
    estimate_initial: float | None = None
    currency: str | None = None
    topk: list[dict] | None = None
    reason: str | None = None

@router.post("/budget/predict", response_model=PredictResponse)
def budget_predict(req: PredictRequest):
    try:
        result = predict_initial_budget(
            np.asarray(req.query_vec_1, dtype="float32"),
            np.asarray(req.query_vec_2, dtype="float32") if req.query_vec_2 else None
        )
        if not result["can_estimate"]:
            raise HTTPException(status_code=422, detail=result.get("reason", "cannot estimate"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"prediction failed: {e}")
