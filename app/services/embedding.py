import re
import hashlib
import os
import numpy as np
from typing import Optional

from app.core.config import settings

_client_singleton = None

_token_re = re.compile(r"\w+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return _token_re.findall(text.lower())


def _rand_vec_for_token(token: str, dim: int) -> np.ndarray:
    # Use stable hash to seed RNG per token
    h = hashlib.md5(token.encode("utf-8")).digest()
    seed = int.from_bytes(h[:8], "little", signed=False) & 0x7FFF_FFFF
    rng = np.random.default_rng(seed)
    v = rng.normal(0.0, 1.0, size=dim).astype("float32")
    return v


def _ensure_openai_client():
    global _client_singleton
    if _client_singleton is not None:
        return _client_singleton
    try:
        from openai import OpenAI
    except Exception as e:
        raise RuntimeError("openai package is required for EMBEDDING_PROVIDER=openai") from e
    api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    client = OpenAI(api_key=api_key, base_url=settings.OPENAI_BASE_URL or None)
    _client_singleton = client
    return client


def _embed_openai(text: str) -> np.ndarray:
    client = _ensure_openai_client()
    model = settings.OPENAI_EMBEDDING_MODEL
    # OpenAI SDK v1
    resp = client.embeddings.create(model=model, input=text)
    emb = resp.data[0].embedding
    return np.asarray(emb, dtype="float32")


def _embed_dummy(text: str, dim: int, normalize: bool = True) -> np.ndarray:
    tokens = _tokenize(text or "")
    if not tokens:
        raise ValueError("empty text for embedding")
    vec = np.zeros((dim,), dtype="float32")
    for t in tokens:
        vec += _rand_vec_for_token(t, dim)
    if normalize:
        n = float(np.linalg.norm(vec) + 1e-12)
        vec = (vec / n).astype("float32")
    return vec


def embed_text_to_vec(text: str, dim: int, normalize: bool = True) -> np.ndarray:
    """Provider-aware embedding.
    - If settings.EMBEDDING_PROVIDER == 'openai': returns model-dimension vector.
    - Else: returns dummy embedding of length `dim`.
    NOTE: Predictor expects the query dimension to match X1. Ensure your
    dataset embeddings (adm_game.parquet) were produced by the same model
    when using the OpenAI provider.
    """
    if settings.EMBEDDING_PROVIDER.lower() == "openai":
        v = _embed_openai(text)
        if normalize:
            n = float(np.linalg.norm(v) + 1e-12)
            v = (v / n).astype("float32")
        return v
    # default dummy
    return _embed_dummy(text, dim=dim, normalize=normalize)
