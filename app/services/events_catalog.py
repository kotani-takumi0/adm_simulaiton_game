from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd


@lru_cache(maxsize=1)
def load_events_df() -> pd.DataFrame:
    """
    Load selected game events catalog from CSV.
    Expected columns include:
      - "予算事業ID" (unique id)
      - "事業名", "事業の概要", "府省庁", "局・庁",
        "当初予算", "歳出予算現額", "現状・課題", "事業概要URL"
    The function sets index to stringified id for quick lookup.
    """
    base = Path("data")
    csv_path = base / "selected_game.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"missing events catalog: {csv_path}")
    df = pd.read_csv(csv_path)
    if "予算事業ID" not in df.columns:
        raise ValueError("selected_game.csv must contain column '予算事業ID'")
    # normalize id as string index
    df["_ID_STR_"] = df["予算事業ID"].astype(str)
    df = df.set_index("_ID_STR_", drop=False)
    return df


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
