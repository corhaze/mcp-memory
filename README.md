# mcp-memory

An MCP server that persists project context across LLM sessions — no more re-explaining your stack, decisions, or history.

## How it works

- **Serverless**: Data is stored in `~/.mcp-memory/memory.db` (SQLite — no server needed).
- **Search-First**: Uses FTS5 for ranked, high-performance keyword discovery.
- **Agent-Ready**: Built-in "Orientation" and "Worklog" features to bootstrap new agents.

## Quick Start

```bash
# Requires Python 3.10+
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Tools & Features

### 🔍 Discovery
- `search_insights`: Ranked keyword search across project lessons.
- `search_contexts`: Specifically search through stored facts and config.
- `get_timeline`: Read the chronological history of decisions and milestones.

### 📋 Task Management
- `add_todo`: Create tasks with rich detail (implementation plans, etc.).
- `list_todos`: Filter and browse active work items.
- `update_todo`: Track status transitions (pending ➜ in_progress ➜ completed).

### 🧠 Core Memory
- `set_context` / `get_context`: Store and retrieve specific facts.
- `add_insight`: Save reusable lessons, skills, or "gotchas."
- `summarize`: Export everything to a human-readable `CONTEXT.md`.

## Connect to an MCP client

Add to your client config (e.g. `~/.cursor/mcp.json` or Claude Desktop):

```json
{
  "mcpServers": {
    "memory": {
      "command": "/path/to/mcp-memory/.venv/bin/mcp-memory"
    }
  }
}
```

## Run Tests

```bash
./.venv/bin/python -m pytest tests/ -v
```

## License

MIT - See [LICENSE](LICENSE) for details.
