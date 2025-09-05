# app/api/v1/budget.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import numpy as np
from pathlib import Path

from app.api.v1.state import _SESSIONS  # MVP: セッションKVSを共用
from app.services.predictor import predict_initial_budget
from app.services.datastore import load_budget_data
from app.services.embedding import embed_text_to_vec
from app.utils.json_safe import json_safe

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
    # テキストのみ受け付け（サーバ側で埋め込み）
    query_text: str

class PredictResponse(BaseModel):
    can_estimate: bool
    estimate_initial: float | None = None
    estimate_final: float | None = None
    ratio: float | None = None
    currency: str | None = None
    topk: list[dict] | None = None
    reason: str | None = None

@router.post("/budget/predict", response_model=PredictResponse)
def budget_predict(req: PredictRequest):
    try:
        data = load_budget_data()
        if not req.query_text or not req.query_text.strip():
            raise HTTPException(status_code=422, detail="query_text is required")
        q = embed_text_to_vec(req.query_text, dim=int(data.X1.shape[1]), normalize=True)

        result = predict_initial_budget(q)
        result = json_safe(result)
        if not result["can_estimate"]:
            raise HTTPException(status_code=422, detail=result.get("reason", "cannot estimate"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"prediction failed: {e}")


# ========== 3) モデル情報 (/v1/budget/model_info) ==========

class ModelInfo(BaseModel):
    x_dim: int
    n_items: int
    topk: int
    tau: float
    data_source: str

@router.get("/budget/model_info", response_model=ModelInfo)
def budget_model_info():
    try:
        data = load_budget_data()
        x_dim = int(data.X1.shape[1])
        n_items = int(data.X1.shape[0])
        data_source = "adm_game.parquet" if Path("data/adm_game.parquet").exists() else "embeddings.npz"
        from app.core.config import settings
        return ModelInfo(x_dim=x_dim, n_items=n_items, topk=settings.TOPK, tau=settings.TAU, data_source=data_source)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to load model info: {e}")
