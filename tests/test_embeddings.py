"""
tests/test_embeddings.py — unit tests for embeddings availability logic.

These tests verify the opt-in / graceful-degradation behaviour added in the
'Make semantic search optional' task. They do NOT require fastembed to be
installed — they mock the import to keep things fast and portable.
"""

import importlib
import sys
import pytest
import mcp_memory.embeddings as emb


@pytest.fixture(autouse=True)
def reset_module_state(monkeypatch):
    """Reset embeddings module state between tests."""
    monkeypatch.setattr(emb, "_model", None)
    monkeypatch.setattr(emb, "_model_available", None)
    yield
    monkeypatch.setattr(emb, "_model", None)
    monkeypatch.setattr(emb, "_model_available", None)


def test_is_available_false_by_default(monkeypatch):
    """is_available() returns False when env var is not set."""
    monkeypatch.delenv("MCP_MEMORY_ENABLE_EMBEDDINGS", raising=False)
    assert emb.is_available() is False


def test_is_available_false_when_env_var_not_one(monkeypatch):
    """is_available() returns False when env var is set to a value other than '1'."""
    monkeypatch.setenv("MCP_MEMORY_ENABLE_EMBEDDINGS", "0")
    assert emb.is_available() is False


def test_is_available_false_when_fastembed_raises(monkeypatch):
    """is_available() returns False when fastembed fails to import."""
    monkeypatch.setenv("MCP_MEMORY_ENABLE_EMBEDDINGS", "1")

    # Simulate fastembed being absent or broken
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "fastembed":
            raise ImportError("fastembed not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    assert emb.is_available() is False


def test_is_available_true_when_model_loads(monkeypatch):
    """is_available() returns True when env var is set and model loads successfully."""
    monkeypatch.setenv("MCP_MEMORY_ENABLE_EMBEDDINGS", "1")

    class _FakeModel:
        def embed(self, texts):
            import numpy as np
            return [np.array([0.1, 0.2, 0.3]) for _ in texts]

    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "fastembed":
            module = type(sys)("fastembed")
            module.TextEmbedding = lambda model_name: _FakeModel()
            return module
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    assert emb.is_available() is True


def test_generate_embedding_raises_when_unavailable(monkeypatch):
    """generate_embedding() raises RuntimeError when model is not available."""
    monkeypatch.delenv("MCP_MEMORY_ENABLE_EMBEDDINGS", raising=False)
    with pytest.raises(RuntimeError, match="not available"):
        emb.generate_embedding("some text")


def test_generate_embeddings_raises_when_unavailable(monkeypatch):
    """generate_embeddings() raises RuntimeError when model is not available."""
    monkeypatch.delenv("MCP_MEMORY_ENABLE_EMBEDDINGS", raising=False)
    with pytest.raises(RuntimeError, match="not available"):
        emb.generate_embeddings(["text one", "text two"])


def test_entity_creation_succeeds_when_embeddings_disabled(monkeypatch):
    """create_task() succeeds normally when embeddings are disabled."""
    monkeypatch.delenv("MCP_MEMORY_ENABLE_EMBEDDINGS", raising=False)
    from mcp_memory.db import create_project, create_task
    from mcp_memory.repository.connection import get_conn

    proj = create_project("test-no-embeddings")
    task = create_task(proj.id, "A task without embeddings", description="Should work fine")
    assert task.title == "A task without embeddings"

    # Confirm no embedding row was stored
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM embeddings WHERE entity_id=?", (task.id,)
        ).fetchone()
    assert row["cnt"] == 0


def test_is_available_only_loads_once(monkeypatch):
    """_load_model() is called only once; subsequent is_available() calls are fast."""
    monkeypatch.delenv("MCP_MEMORY_ENABLE_EMBEDDINGS", raising=False)

    call_count = 0
    original_load = emb._load_model

    def counting_load():
        nonlocal call_count
        call_count += 1
        original_load()

    monkeypatch.setattr(emb, "_load_model", counting_load)

    emb.is_available()
    emb.is_available()
    emb.is_available()

    assert call_count == 1
