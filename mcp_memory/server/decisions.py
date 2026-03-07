from typing import Optional
from .mcp import mcp
import mcp_memory.db as _db

# ── Decisions ─────────────────────────────────────────────────────────────────

@mcp.tool()
def create_decision(
    project_id: str,
    title: str,
    decision_text: str,
    rationale: Optional[str] = None,
    status: str = "active",
) -> str:
    """
    Record a durable architecture or workflow decision.

    Decisions are one of the highest-value memory types. Use them for:
    - Technology choices
    - API contracts
    - Data model choices
    - Process decisions

    Args:
        project_id:    Project UUID or name.
        title:         Short decision title.
        decision_text: The decision itself.
        rationale:     Why this decision was made.
        status:        active (default), draft, superseded.
    """
    proj = _db.get_project(project_id)
    if not proj:
        return f"Project '{project_id}' not found."
    dec = _db.create_decision(proj.id, title, decision_text, rationale, status)
    return f"Decision created: '{dec.title}' (id: {dec.id})"


@mcp.tool()
def get_decision(decision_id: str) -> str:
    """
    Retrieve a specific decision.

    Args:
        decision_id: UUID of the decision.
    """
    dec = _db.get_decision(decision_id)
    if not dec:
        return f"Decision '{decision_id}' not found."
    lines = [
        f"Decision: {dec.title}",
        f"Status: {dec.status}",
        f"",
        dec.decision_text,
    ]
    if dec.rationale:
        lines += ["", f"Rationale: {dec.rationale}"]
    if dec.supersedes_decision_id:
        lines.append(f"Supersedes: {dec.supersedes_decision_id}")
    return "\n".join(lines)


@mcp.tool()
def list_decisions(
    project_id: str,
    status: Optional[str] = None,
) -> str:
    """
    List decisions for a project.

    Args:
        project_id: Project UUID or name.
        status:     Filter by status — active, draft, superseded.
    """
    proj = _db.get_project(project_id)
    if not proj:
        return f"Project '{project_id}' not found."
    decisions = _db.list_decisions(proj.id, status)
    if not decisions:
        return "No decisions found."
    lines = [f"[{d.status}] {d.title} ({d.id})" for d in decisions]
    return f"{len(decisions)} decision(s):\n" + "\n".join(lines)


@mcp.tool()
def update_decision(
    decision_id: str,
    title: Optional[str] = None,
    decision_text: Optional[str] = None,
    rationale: Optional[str] = None,
    status: Optional[str] = None,
) -> str:
    """
    Update a decision's fields.

    Args:
        decision_id:   UUID of the decision.
        title:         New title.
        decision_text: New decision text.
        rationale:     New rationale.
        status:        active, draft, or superseded.
    """
    dec = _db.update_decision(decision_id, title, decision_text, rationale, status)
    if not dec:
        return f"Decision '{decision_id}' not found."
    return f"Updated decision '{dec.title}' — status: {dec.status}"


@mcp.tool()
def supersede_decision(
    old_decision_id: str,
    project_id: str,
    title: str,
    decision_text: str,
    rationale: Optional[str] = None,
) -> str:
    """
    Create a new decision that supersedes an existing one.
    The old decision is automatically marked 'superseded'.

    Args:
        old_decision_id: UUID of the decision being replaced.
        project_id:      Project UUID or name.
        title:           Title of the new decision.
        decision_text:   The new decision text.
        rationale:       Why the old decision was superseded.
    """
    proj = _db.get_project(project_id)
    if not proj:
        return f"Project '{project_id}' not found."
    new_dec = _db.supersede_decision(old_decision_id, proj.id, title, decision_text, rationale)
    return (f"Decision superseded. New decision: '{new_dec.title}' (id: {new_dec.id}). "
            f"Old decision {old_decision_id[:8]} marked superseded.")
