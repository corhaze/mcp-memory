
import pytest
from mcp_memory.db import (
    upsert_context,
    add_insight,
    upsert_todo,
    semantic_search_contexts,
    semantic_search_insights,
    semantic_search_todos,
    get_conn
)

@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr("mcp_memory.db.db_path", lambda: db_file)
    # Ensure foreign keys are on
    with get_conn() as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
    yield db_file

def test_semantic_search_contexts():
    # Setup context
    upsert_context("proj", "lang", "Python is the primary language.")
    upsert_context("proj", "db", "We use SQLite for storage.")
    
    # Search for something related but without exact keywords
    results = semantic_search_contexts("What programming language do we use?", project="proj")
    
    assert len(results) > 0
    assert "Python" in results[0].value
    
def test_semantic_search_insights():
    add_insight("Testing Guide", "Always use pytest for unit tests and follow patterns.", scope="proj")
    add_insight("Deployment", "Deploy to production using the CI/CD pipeline.", scope="proj")
    
    # Search for testing related info
    results = semantic_search_insights("How should I verify my code?", scope="proj")
    
    assert len(results) > 0
    assert "pytest" in results[0].body
    assert results[0].title == "Testing Guide"

def test_semantic_search_todos():
    upsert_todo("proj", "Refactor Auth", "Clean up the login logic and session handling.")
    upsert_todo("proj", "Update Docs", "Write some more documentation for the API.")
    
    # Search for login related tasks
    results = semantic_search_todos("authentication and sign-in tasks", project="proj")
    
    assert len(results) > 0
    assert "Auth" in results[0].title
    assert "login" in results[0].description
