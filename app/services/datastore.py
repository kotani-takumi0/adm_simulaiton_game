from dataclasses import dataclass
from functools import lru_cache
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

@lru_cache(maxsize=1)
def load_budget_data() -> BudgetData:
    base = Path("data")
    npz = np.load(base / "embeddings.npz")  # 例: {X1, X2, y_init, y_final?}
    X1 = np.asarray(npz["X1"], dtype="float32")
    X2 = np.asarray(npz["X2"], dtype="float32") if "X2" in npz else np.zeros((X1.shape[0], 1), "float32")
    y_init = np.asarray(npz["y_init"], dtype="float64")
    y_final = np.asarray(npz["y_final"], dtype="float64") if "y_final" in npz else None

    # メタデータ（parquet推奨。無ければCSV）
    meta_path = base / "events.parquet"
    if meta_path.exists():
        df = pd.read_parquet(meta_path)
    else:
        df = pd.read_csv(base / "events.csv")

    return BudgetData(X1=X1, X2=X2, y_init=y_init, y_final=y_final, df=df)
