import numpy as np
import pandas as pd
from typing import Any
from app.core.config import settings
from app.services.datastore import load_budget_data, BudgetData

def _normalize_rows(M: np.ndarray) -> np.ndarray:
    M = np.asarray(M, dtype="float32")
    if M.ndim == 1: M = M[None, :]
    n = np.linalg.norm(M, axis=1, keepdims=True) + 1e-12
    return M / n

def _softmax_1d(x: np.ndarray, tau: float) -> np.ndarray:
    z = x / tau
    z -= z.max()
    e = np.exp(z)
    return e / (e.sum() + 1e-12)

def _weighted_log_mean(values: np.ndarray, weights: np.ndarray) -> float:
    v = np.asarray(values, dtype="float64")
    w = np.asarray(weights, dtype="float64")
    return float(np.exp((w * np.log(v)).sum()))

def predict_initial_budget(query_vec_1: np.ndarray,
                           query_vec_2: np.ndarray | None = None) -> dict[str, Any]:
    """当初予算の推定とTop-K根拠を返す。"""
    data: BudgetData = load_budget_data()
    X1_n = _normalize_rows(data.X1)
    X2_n = _normalize_rows(data.X2)
    Q1_n = _normalize_rows(np.asarray(query_vec_1, "float32"))
    Q2_n = _normalize_rows(np.asarray(query_vec_2, "float32")) if query_vec_2 is not None else None

    S1 = Q1_n @ X1_n.T
    S2 = Q2_n @ X2_n.T if Q2_n is not None else 0.0
    S  = settings.ALPHA * S1 + settings.BETA * (S2 if isinstance(S2, np.ndarray) else 0.0)

    scores = S[0]  # 単一クエリ想定
    K = int(min(settings.TOPK, scores.shape[0]))
    idx = np.argpartition(-scores, K-1)[:K]
    idx = idx[np.argsort(-scores[idx])]
    sims = scores[idx]
    weights = _softmax_1d(sims, tau=settings.TAU)

    init_budget = data.y_init[idx].astype("float64")
    mask = np.isfinite(init_budget) & (init_budget > 0)
    if mask.sum() == 0:
        return {"can_estimate": False, "reason": "no valid initial budget in top-k"}

    # マスク適用＆重み再正規化
    sims_f = sims[mask]
    w_f = weights[mask]
    init_f = init_budget[mask]
    w_f = w_f / (w_f.sum() + 1e-12)

    est_init = _weighted_log_mean(init_f, w_f)

    # 根拠テーブル
    df = data.df
    col_name   = "事業名" if "事業名" in df.columns else None
    col_init   = "当初予算" if "当初予算" in df.columns else None

    rows = []
    for rank, j in enumerate(idx[mask], 1):
        row = df.iloc[int(j)]
        name  = row[col_name] if col_name else ""
        y0    = float(row[col_init]) if col_init and pd.notna(row[col_init]) else float("nan")
        rows.append({
            "rank": rank,
            "df_index": int(j),
            "similarity": float(sims_f[rank-1]),
            "weight": float(w_f[rank-1]),
            "name": name,
            "initial_budget": y0,
        })

    return {
        "can_estimate": True,
        "estimate_initial": est_init,
        "currency": "JPY",
        "topk": rows
    }
