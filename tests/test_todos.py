import pytest
from mcp_memory.db import upsert_todo, get_todo, list_todos, search_todos, delete_todo, _init_schema, get_conn

def test_todo_lifecycle(tmp_path):
    # Use a temporary database for testing
    import os
    os.environ["MCP_MEMORY_DB"] = str(tmp_path / "test.db")
    with get_conn() as conn:
        _init_schema(conn)

    # Create
    t1 = upsert_todo("proj1", "Task 1", "Description 1", priority="high")
    assert t1.title == "Task 1"
    assert t1.priority == "high"
    assert t1.status == "pending"

    # Get
    t1_get = get_todo(t1.id)
    assert t1_get.id == t1.id
    assert t1_get.description == "Description 1"

    # Update
    t1_up = upsert_todo("proj1", "Task 1 Updated", "New Plan", status="in_progress", todo_id=t1.id)
    assert t1_up.id == t1.id
    assert t1_up.status == "in_progress"
    assert t1_up.description == "New Plan"

    # List
    todos = list_todos("proj1")
    assert len(todos) == 1
    
    upsert_todo("proj1", "Task 2", "Desc 2", status="completed")
    all_todos = list_todos("proj1")
    assert len(all_todos) == 2
    
    pending = list_todos("proj1", status="pending")
    assert len(pending) == 0 # T1 is in_progress, T2 is completed
    
    # Search
    results = search_todos("Plan")
    assert len(results) == 1
    assert results[0].id == t1.id

    # Delete
    assert delete_todo(t1.id) is True
    assert get_todo(t1.id) is None
    assert len(list_todos("proj1")) == 1
