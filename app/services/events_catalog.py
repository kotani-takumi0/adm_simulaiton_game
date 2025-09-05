from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def _normalize_id_series(s: pd.Series) -> pd.Series:
    def _norm_id(v):
        try:
            f = float(v)
            if np.isfinite(f) and abs(f - int(f)) < 1e-9:
                return str(int(f))
        except Exception:
            pass
        v_str = str(v).strip()
        if v_str.endswith(".0"):
            return v_str[:-2]
        return v_str
    return s.map(_norm_id)


@lru_cache(maxsize=1)
def load_events_df() -> pd.DataFrame:
    """Load events metadata, preferring selected_game.csv, but also merging adm_game.parquet.
    Index is normalized string of 予算事業ID. Rows from selected_game.csv take precedence.
    """
    base = Path("data")
    df_sel: pd.DataFrame | None = None
    df_all: pd.DataFrame | None = None

    csv_path = base / "selected_game.csv"
    if csv_path.exists():
        df_sel = pd.read_csv(csv_path)
        if "予算事業ID" not in df_sel.columns:
            raise ValueError("selected_game.csv must contain column '予算事業ID'")
        df_sel["_ID_STR_"] = _normalize_id_series(df_sel["予算事業ID"]) 
        df_sel = df_sel.set_index("_ID_STR_", drop=False)

    parq_path = base / "adm_game.parquet"
    if parq_path.exists():
        try:
            df_all = pd.read_parquet(parq_path)
            if "予算事業ID" in df_all.columns:
                df_all["_ID_STR_"] = _normalize_id_series(df_all["予算事業ID"]) 
                df_all = df_all.set_index("_ID_STR_", drop=False)
            else:
                df_all = None
        except Exception:
            df_all = None

    if df_sel is not None and df_all is not None:
        # Combine: selected overrides adm
        # Align columns
        missing_cols = [c for c in df_sel.columns if c not in df_all.columns]
        for c in missing_cols:
            df_all[c] = np.nan
        missing_cols2 = [c for c in df_all.columns if c not in df_sel.columns]
        for c in missing_cols2:
            df_sel[c] = np.nan
        # concat, drop duplicates keeping first (df_sel first)
        df = pd.concat([df_sel, df_all.loc[~df_all.index.isin(df_sel.index)]], axis=0)
        return df
    if df_sel is not None:
        return df_sel
    if df_all is not None:
        return df_all
    raise FileNotFoundError("No events metadata found: selected_game.csv or adm_game.parquet")


def get_all_event_ids() -> list[str]:
    df = load_events_df()
    return df.index.astype(str).tolist()


def get_event_meta(event_id: str) -> dict[str, Any]:
    df = load_events_df()
    key = str(event_id)
    if key not in df.index:
        raise KeyError(f"event id not found: {event_id}")
    row = df.loc[key]
    # return a compact subset while keeping original columns when present
    result: dict[str, Any] = {
        "予算事業ID": key,
        "事業名": row.get("事業名", None),
        "事業の概要": row.get("事業の概要", None),
        "府省庁": row.get("府省庁", None),
        "局・庁": row.get("局・庁", None),
        "当初予算": row.get("当初予算", None),
        "歳出予算現額": row.get("歳出予算現額", None),
        "現状・課題": row.get("現状・課題", None),
        "事業概要URL": row.get("事業概要URL", None),
    }
    return result
