# mcp-memory

An MCP server that persists project context across LLM sessions — no more re-explaining your stack, decisions, or history.

## How it works

- **Serverless**: Data is stored in `~/.mcp-memory/memory.db` (SQLite — no server needed).
- **Hybrid Search**: FTS5 keyword search + semantic vector search (FastEmbed) for comprehensive retrieval.
- **Relational + Semantic**: Structured projects/tasks/decisions with semantic embeddings for fuzzy recall.
- **Agent-Ready**: `get_working_context` bootstraps any new agent with current summary, open tasks, and linked decisions in one call.

## Quick Start

```bash
# Requires Python 3.9+
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Tools & Features

### Projects & Context
- `create_project` / `list_projects`: Manage project workspaces.
- `add_project_summary`: Rolling summaries for cheap session rehydration.
- `get_working_context`: One-call orientation snapshot — summary + open tasks + decisions.

### Tasks
- `create_task` / `update_task`: Track work with status, priority, subtasks, and blocking relationships.
- `log_task_event`: Append-only history for any task.
- `get_task_tree`: View a task with all its subtasks.

### Decisions
- `create_decision`: Record durable architecture choices with rationale.
- `supersede_decision`: Mark a decision as replaced by a newer one.

### Notes
- `create_note` / `list_notes`: Flexible operational memory (investigation, context, bug, handover).

### Search
- `search` / `search_tasks` / `search_decisions` / `search_notes`: FTS5 keyword search.
- `semantic_search_tasks` / `semantic_search_decisions` / `semantic_search_notes`: Vector-based fuzzy search.

### Links
- `create_link` / `get_links`: Connect related records (task→decision, note→task, etc).

## Connect to an MCP client

Add to your client config (e.g. `~/.claude.json` or Claude Desktop):

```json
{
  "mcpServers": {
    "mcp-memory": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "/path/to/mcp-memory", "mcp-memory"]
    }
  }
}
```

Or with pip install:

```json
{
  "mcpServers": {
    "mcp-memory": {
      "command": "/path/to/mcp-memory/.venv/bin/mcp-memory"
    }
  }
}
```

## Migrating from the old mcp-memory schema

If you have data from the previous version of mcp-memory (contexts, insights, todos, events), run:

```bash
mcp-memory-cli migrate
```

This will:
1. Read your existing `~/.mcp-memory/memory.db` (old schema: contexts, insights, todos, events)
2. Create projects from the project names found in your data
3. Convert **contexts** → notes (type: `context`)
4. Convert **todos** → tasks (preserving status, priority, and subtasks)
5. Convert **insights** → notes (type: `insight`)
6. Convert **events** → notes (type: `event`)
7. Generate semantic embeddings for all migrated data

The migration is safe to run multiple times — existing projects in the new schema are not overwritten.

## Web Explorer UI

Start the local web UI to browse projects, tasks, decisions, and notes:

```bash
uvicorn mcp_memory.ui_server:app --port 7878
```

Then open http://localhost:7878.

## Run Tests

```bash
./.venv/bin/python -m pytest tests/ -v
```

## License

MIT - See [LICENSE](LICENSE) for details.
