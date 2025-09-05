import math
from typing import Any

try:
    import numpy as np  # type: ignore
except Exception:
    np = None  # type: ignore


def _is_nan_or_inf(x: Any) -> bool:
    try:
        f = float(x)
    except Exception:
        return False
    return not math.isfinite(f)


def json_safe(obj: Any) -> Any:
    """Recursively convert NaN/Inf to None and numpy scalars to Python types.
    Also handles lists/tuples/dicts.
    """
    # numpy scalar → Python scalar
    if np is not None and isinstance(obj, (np.generic,)):
        obj = obj.item()

    if isinstance(obj, (float, int)):
        return None if _is_nan_or_inf(obj) else obj
    if isinstance(obj, str):
        # common textual nan
        return None if obj.lower() == 'nan' else obj
    if isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(v) for v in obj]
    return obj

