from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="mcp-memory",
    instructions=(
        "Use this server to persist and recall project context across sessions. "

        "SESSION START (MANDATORY): Always call `get_working_context` at the start of every "
        "session. It returns the current summary, open tasks, linked decisions, and global notes "
        "(with full text) in one call. Global notes contain cross-project coding philosophy, "
        "quality standards, and process rules — read them before taking any action. "
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
        "(2) search for keyword lookup (always available), "
        "(3) semantic_search_* for fuzzy recall when keywords fail — requires "
        "MCP_MEMORY_ENABLE_EMBEDDINGS=1; if unavailable the tool will say so, "
        "fall back to `search` in that case, "
        "(4) get_links for graph traversal. "

        "ANSWERING QUESTIONS (MANDATORY): Before reading any code file to answer a question "
        "about the project, always search the memory bank first using `search` or "
        "`semantic_search_*`. Notes, task notes, and decisions frequently contain the answer "
        "or directly relevant context — investigation findings, past debugging sessions, "
        "architecture rationale, and gotchas are stored here precisely so you don't have to "
        "re-derive them from code. Code exploration is a fallback for when memory search "
        "yields insufficient results, not the first step. "

        "TASKS: Status flow: open → in_progress → blocked/done/cancelled. "
        "CRITICAL: Before starting work on any task or subtask, immediately call update_task "
        "to set status to in_progress. Do this before writing any code, editing any file, "
        "or taking any implementation action. This applies to subtasks as well as top-level tasks. "
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

        "CODE QUALITY: See the 'Code quality standards' global note loaded by get_working_context."
    ),
)
