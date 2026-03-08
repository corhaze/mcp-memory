from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="mcp-memory",
    instructions=(
        "Use this server to persist and recall project context across sessions. "

        "SESSION START (MANDATORY): Always call `get_working_context` at the start of every "
        "session. It returns the current summary, open tasks, linked decisions, and global notes "
        "in one call. Global notes contain cross-project coding philosophy and style rules — "
        "read them before making any implementation decisions. "
        "Never begin work without orienting yourself first. "

        "PROJECT SETUP (MANDATORY): When creating a new project, you MUST immediately: "
        "(1) call `create_project`, "
        "(2) create tasks for all known work with `create_task`, "
        "(3) call `add_project_summary` with a stable prose overview covering the goal, "
        "tech stack, and key architectural decisions. Write it as an introduction to the project, "
        "not a status update — it should remain accurate for the lifetime of the project. "
        "A project without a summary is incomplete. "

        "KEEPING RECORDS CURRENT (MANDATORY): You MUST update records as you work — do not "
        "batch updates to the end of a session. Specifically: "
        "- Move tasks to `in_progress` when you start them, `done` when complete. "
        "- Call `log_task_event` after each meaningful step on a task. "
        "- CRITICAL: Use `create_task_note` frequently to document findings, failures, "
        "  gotchas, and attempt records specific to a task. Do NOT just rely on the event log. "
        "- Call `create_decision` immediately when any architecture or design choice is made. "
        "- Call `create_note` when you discover something non-obvious. "
        "Current project state is expressed through tasks, not the summary. "
        "Failing to update records defeats the purpose of this server. "

        "RETRIEVAL ORDER: (1) get_working_context for relational state, "
        "(2) search/search_* for keyword lookup, "
        "(3) semantic_search_* for fuzzy recall when keywords fail, "
        "(4) get_links for graph traversal. "

        "TASKS: Status flow: open → in_progress → blocked/done/cancelled. "
        "Use parent_task_id for subtasks. Use blocked_by_task_id to express dependencies. "
        "When inspecting a task, always call `list_task_notes` to retrieve task-scoped notes — "
        "these are separate from project notes and will not appear in get_working_context. "
        "Use `create_task_note` to record task-specific findings, attempts, and observations. "

        "DECISIONS: Use create_decision for durable architecture choices with rationale. "
        "Use supersede_decision when a decision is replaced — never silently overwrite. "

        "NOTES: Use create_note for operational memory. Types: investigation, implementation, "
        "bug, context, handover. Prefer notes over comments in code for cross-session findings. "

        "LINKS: Use create_link to connect related records (task→decision, note→task, etc). "
        "Link types: relates_to, implements, blocks, derived_from, explains, supersedes. "

        "CODE QUALITY (MANDATORY): Always prioritise clean, modular, idiomatic code. "
        "Write small, well-defined functions — one clear purpose per function. "
        "Follow language conventions: Python (PEP 8, type hints, dataclasses/Pydantic), "
        "JavaScript (const/let, async/await, descriptive names, no var). "
        "No premature abstraction — wait for a pattern to repeat before extracting. "
        "Readable over clever. If in doubt, keep it simple."
    ),
)
