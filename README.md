# mcp-memory

An MCP server that persists project context across LLM sessions — no more re-explaining your stack, decisions, or history.

## How it works

- **Serverless**: Data lives in `~/.mcp-memory/memory.db` (SQLite — no server, no Docker).
- **Hybrid Search**: FTS5 keyword search + semantic vector search (FastEmbed) for comprehensive retrieval.
- **Relational + Semantic**: Structured projects, tasks, decisions, and notes with semantic embeddings for fuzzy recall.
- **Agent-Ready**: `get_working_context` bootstraps any new agent session with the current project summary, open tasks, linked decisions, and global notes in a single call.
- **Web UI**: Local terminal-aesthetic explorer for browsing and editing all project data.

## Quick Start

Requires Python ≥ 3.11 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/corhaze/mcp-memory
cd mcp-memory
uv sync --all-extras
```

> **First run:** FastEmbed downloads the embedding model (`BAAI/bge-small-en-v1.5`, ~130 MB) to `~/.cache/fastembed/` on first use. Subsequent starts are instant.

## Connect to an MCP client

Add to your client config (e.g. Claude Desktop or `~/.claude.json`):

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

## MCP Tools

### Session startup
- `get_working_context`: One-call orientation — project summary, open/in-progress tasks, linked decisions, and full global notes text. Call this at the start of every session.

### Projects
- `create_project` / `list_projects` / `update_project`
- `add_project_summary`: Set a stable prose overview of the project (goal, stack, key decisions).
- `get_project_summary`: Retrieve the current summary.

### Tasks
- `create_task` / `update_task` / `delete_task`: Track work with status, urgency, complexity, subtasks, and blocking relationships.
- `create_task_note` / `list_task_notes`: Scoped notes on a specific task — findings, attempts, gotchas.
- `log_task_event` / `get_task_events`: Append-only event history per task.
- `get_task` / `list_tasks`: Retrieve individual tasks or filtered lists.

### Decisions
- `create_decision`: Record durable architecture choices with rationale.
- `update_decision` / `supersede_decision`: Evolve decisions over time without losing history.
- `list_decisions` / `get_decision`

### Notes
- `create_note` / `update_note` / `delete_note`: Flexible operational memory — types: `investigation`, `implementation`, `bug`, `context`, `handover`.
- `list_notes` / `get_note`

### Global Notes
- `create_global_note`: Cross-project philosophy, coding standards, and process rules loaded into every session.
- `list_global_notes` / `update_global_note` / `delete_global_note`

### Search
- `search`: FTS5 keyword search across tasks, decisions, notes, and document chunks.
- `semantic_search_tasks` / `semantic_search_decisions` / `semantic_search_notes` / `semantic_search_task_notes`: Vector-based fuzzy search.

### Links
- `create_link` / `get_links`: Connect related records (task→decision, note→task, etc.) with typed relationships.

### Documents
- `create_document` / `list_documents`: Store and retrieve larger reference documents with chunked semantic indexing.

## Web UI

Browse and edit all project data in a local terminal-aesthetic UI:

```bash
uv run uvicorn mcp_memory.ui_server:app --reload --reload-dir mcp_memory --port 7878
```

Then open http://localhost:7878.

> **Important:** Always pass `--reload-dir mcp_memory` when using `--reload`. Without it, uvicorn watches the entire project directory including the SQLite WAL/SHM files, causing a rapid reload loop, ONNX thread accumulation, and severe CPU pressure.

## Development

### Run tests

```bash
uv run pytest tests/ -q
```

### Install pre-commit hook

Automatically runs the test suite before every commit:

```bash
bash scripts/install-hooks.sh
```

### Custom database location

By default the database is created at `~/.mcp-memory/memory.db`. Override with an environment variable:

```bash
MCP_MEMORY_DB_PATH=/custom/path/memory.db uv run mcp-memory
```

## License

MIT — see [LICENSE](LICENSE) for details.
