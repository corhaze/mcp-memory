---
description: How to plan a new feature
---

# Feature Planning Workflow

When a user asks you to spec out or plan a new feature, follow this exact workflow:

1. **Understand the Goal**: Read the existing project summaries, active decisions, and open tasks (usually acquired via `get_working_context` at the start of the session).
2. **Draft the Implementation Plan**: Create or update the `implementation_plan.md` artifact with a detailed, file-by-file breakdown of what needs to be changed.
3. **Decompose the Work**: Break the implementation plan down into discrete, actionable sub-tasks.
4. **Update Local Tracking**: Add these sub-tasks to the local `task.md` tracking artifact.
5. **SYNC WITH MCP MEMORY (REQUIRED)**: For *every single subtask* you just added to the `task.md`, you MUST invoke the `mcp_mcp-memory_create_task` tool.
   - You must link each subtask to the relevant parent feature task using the `parent_task_id` argument.
   - If a parent task does not exist, create it first.
6. **Request Review**: Notify the user to review the implementation plan. Ensure you do not begin execution until the user has approved the plan explicitly.
