import numpy as np
import pandas as pd
from typing import Any
from app.core.config import settings
from app.services.datastore import load_budget_data, BudgetData
import math

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

def predict_initial_budget(query_vec: np.ndarray) -> dict[str, Any]:
    """当初予算の推定とTop-K根拠を返す（単一クエリベクトル）。

    既存の X1（目的・課題の埋め込み）のみを使用し、線形結合は行わない。
    """
    data: BudgetData = load_budget_data()
    X_n = _normalize_rows(data.X1)
    Q_n = _normalize_rows(np.asarray(query_vec, "float32"))

    if Q_n.shape[1] != X_n.shape[1]:
        return {"can_estimate": False, "reason": f"query dim {Q_n.shape[1]} != X1 dim {X_n.shape[1]}"}

    S = Q_n @ X_n.T

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

    # 現額の推定（任意）
    est_final: float | None = None
    if data.y_final is not None:
        yfin_all = np.asarray(data.y_final[idx].astype("float64"))
        mask_fin = np.isfinite(yfin_all) & (yfin_all > 0)
        if mask_fin.any():
            yfin = yfin_all[mask_fin]
            w_fin = weights[mask_fin]
            w_fin = w_fin / (w_fin.sum() + 1e-12)
            est_final = _weighted_log_mean(yfin, w_fin)

    # 根拠テーブル
    df = data.df
    col_name   = "事業名" if "事業名" in df.columns else None
    col_init   = "当初予算" if "当初予算" in df.columns else None
    col_final  = "歳出予算現額" if "歳出予算現額" in df.columns else None
    col_id     = "予算事業ID" if "予算事業ID" in df.columns else None

    rows = []
    for rank, j in enumerate(idx[mask], 1):
        row = df.iloc[int(j)]
        name  = row[col_name] if col_name else ""
        y0    = float(row[col_init]) if col_init and pd.notna(row[col_init]) else float("nan")
        yfin  = float(row[col_final]) if col_final and pd.notna(row[col_final]) else float("nan")
        rows.append({
            "rank": rank,
            "df_index": int(j),
            "similarity": float(sims_f[rank-1]),
            "weight": float(w_f[rank-1]),
            "name": name,
            "initial_budget": (None if (not math.isfinite(y0)) else y0),
            "final_budget": (None if (not math.isfinite(yfin)) else yfin),
            "budget_id": str(row[col_id]) if col_id and pd.notna(row[col_id]) else None,
        })

    ratio = (est_final / est_init) if (est_final is not None and est_init > 0) else None
    return {
        "can_estimate": True,
        "estimate_initial": est_init,
        "estimate_final": (None if (est_final is None or not math.isfinite(est_final)) else est_final),
        "ratio": (None if (ratio is None or not math.isfinite(ratio)) else ratio),
        "currency": "JPY",
        "topk": rows
    }
