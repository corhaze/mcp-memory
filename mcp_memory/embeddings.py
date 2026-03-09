"""
embeddings.py — Optional vector embedding support using FastEmbed.

Embeddings are DISABLED by default. Set MCP_MEMORY_ENABLE_EMBEDDINGS=1 to opt in.

When disabled (or when the model fails to load), is_available() returns False
and entity creation continues normally — just without embedding storage.
"""

import logging
import os
from typing import List, Optional

_model = None
_model_available: Optional[bool] = None  # None = not yet attempted


def _load_model() -> None:
    global _model, _model_available
    if os.environ.get("MCP_MEMORY_ENABLE_EMBEDDINGS") != "1":
        _model_available = False
        return
    try:
        from fastembed import TextEmbedding
        _model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        _model_available = True
    except Exception as e:
        logging.warning(f"Embeddings unavailable: {e}")
        _model_available = False


def is_available() -> bool:
    """Return True if the embedding model is loaded and ready."""
    if _model_available is None:
        _load_model()
    return bool(_model_available)


def generate_embedding(text: str) -> List[float]:
    """Generate a single embedding for the given text.

    Raises RuntimeError if the model is not available — callers should check
    is_available() first or guard the call site.
    """
    if not is_available():
        raise RuntimeError("Embedding model not available")
    embeddings = list(_model.embed([text]))
    return embeddings[0].tolist()


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a list of texts.

    Raises RuntimeError if the model is not available.
    """
    if not is_available():
        raise RuntimeError("Embedding model not available")
    embeddings = list(_model.embed(texts))
    return [e.tolist() for e in embeddings]


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    import numpy as np
    a = np.array(v1)
    b = np.array(v2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
