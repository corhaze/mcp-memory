"""
embeddings.py — Utility for generating vector embeddings using FastEmbed.
"""

from typing import List
import numpy as np
from fastembed import TextEmbedding

# Initialize the model once. FastEmbed downloads the model on first use.
# Using 'BAAI/bge-small-en-v1.5' as it is fast and efficient for CPU.
_model = None

def get_model():
    global _model
    if _model is None:
        _model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _model

def generate_embedding(text: str) -> List[float]:
    """Generate a single embedding for the given text."""
    model = get_model()
    # model.embed returns a generator
    embeddings = list(model.embed([text]))
    return embeddings[0].tolist()

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a list of texts."""
    model = get_model()
    embeddings = list(model.embed(texts))
    return [e.tolist() for e in embeddings]

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a = np.array(v1)
    b = np.array(v2)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
