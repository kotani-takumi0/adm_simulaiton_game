from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable
import ast
import json
import numpy as np
import pandas as pd
from pathlib import Path

@dataclass(frozen=True)
class BudgetData:
    X1: np.ndarray  # (N, d1) 目的・課題の埋め込み
    X2: np.ndarray  # (N, d2) 事業概要の埋め込み（無ければゼロ配列に）
    y_init: np.ndarray  # (N,) 当初予算
    y_final: np.ndarray | None  # (N,) 現額（無ければ None）
    df: pd.DataFrame           # メタ（事業名など）

def _parse_embedding_cell(x) -> np.ndarray:
    """Parse a single cell from the embedding_sum column into 1D float32 array.
    Accepts list/tuple/ndarray directly, or stringified JSON/Python list.
    """
    if isinstance(x, (list, tuple, np.ndarray)):
        return np.asarray(x, dtype="float32")
    if isinstance(x, str):
        s = x.strip()
        try:
            obj = json.loads(s)
        except Exception:
            try:
                obj = ast.literal_eval(s)
            except Exception:
                raise ValueError("embedding_sum contains non-parsable string entry")
        return np.asarray(obj, dtype="float32")
    raise ValueError("embedding_sum contains unsupported type")


def _stack_embeddings(col: Iterable) -> np.ndarray:
    rows = []
    dim = None
    for v in col:
        arr = _parse_embedding_cell(v)
        if arr.ndim != 1:
            raise ValueError("each embedding must be 1D")
        if dim is None:
            dim = arr.shape[0]
        elif arr.shape[0] != dim:
            raise ValueError("inconsistent embedding dimensions in embedding_sum")
        rows.append(arr)
    if not rows:
        return np.zeros((0, 0), dtype="float32")
    return np.stack(rows, axis=0).astype("float32", copy=False)


@lru_cache(maxsize=1)
def load_budget_data() -> BudgetData:
    base = Path("data")
    parq = base / "adm_game.parquet"

    if parq.exists():
        df = pd.read_parquet(parq)
        if "embedding_sum" not in df.columns:
            raise KeyError("adm_game.parquet must contain column 'embedding_sum'")
        # X: use only embedding_sum as single feature set
        X1 = _stack_embeddings(df["embedding_sum"].tolist())
        # X2 is unused in current predictor; keep a minimal placeholder for compatibility
        X2 = np.zeros((X1.shape[0], 1), dtype="float32")
        # Targets: prefer Japanese column names if present
        if "当初予算" in df.columns:
            y_init = np.asarray(df["当初予算"].values, dtype="float64")
        else:
            # fallback to NaN vector to allow predictor's mask handling
            y_init = np.full((X1.shape[0],), np.nan, dtype="float64")
        y_final = None
        for cand in ("歳出予算現額", "現額", "y_final"):
            if cand in df.columns:
                y_final = np.asarray(df[cand].values, dtype="float64")
                break
        return BudgetData(X1=X1, X2=X2, y_init=y_init, y_final=y_final, df=df)

    # Fallback to legacy files if adm_game.parquet is absent
    npz = np.load(base / "embeddings.npz")  # 例: {X1, X2, y_init, y_final?}
    X1 = np.asarray(npz["X1"], dtype="float32")
    X2 = np.asarray(npz["X2"], dtype="float32") if "X2" in npz else np.zeros((X1.shape[0], 1), "float32")
    y_init = np.asarray(npz["y_init"], dtype="float64")
    y_final = np.asarray(npz["y_final"], dtype="float64") if "y_final" in npz else None

    # メタデータ（優先順: events.parquet > selected_game.csv > events.csv）
    if (base / "events.parquet").exists():
        df = pd.read_parquet(base / "events.parquet")
    elif (base / "selected_game.csv").exists():
        df = pd.read_csv(base / "selected_game.csv")
    else:
        df = pd.read_csv(base / "events.csv")

    return BudgetData(X1=X1, X2=X2, y_init=y_init, y_final=y_final, df=df)
