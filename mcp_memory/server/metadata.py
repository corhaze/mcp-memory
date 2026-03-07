from typing import Optional
from .mcp import mcp
import mcp_memory.db as _db

# ── Entity Links ──────────────────────────────────────────────────────────────

@mcp.tool()
def create_link(
    project_id: str,
    from_entity_type: str,
    from_entity_id: str,
    link_type: str,
    to_entity_type: str,
    to_entity_id: str,
) -> str:
    """
    Create a typed link between any two entities.

    Link types: relates_to, implements, blocks, derived_from, explains, supersedes.
    Entity types: task, decision, note, document, summary.

    Example: link a task to the decision it implements:
      create_link(proj, 'task', task_id, 'implements', 'decision', dec_id)

    Args:
        project_id:       Project UUID or name.
        from_entity_type: Source entity type.
        from_entity_id:   Source entity UUID.
        link_type:        Relationship type.
        to_entity_type:   Target entity type.
        to_entity_id:     Target entity UUID.
    """
    proj = _db.get_project(project_id)
    if not proj:
        return f"Project '{project_id}' not found."
    lnk = _db.create_link(proj.id, from_entity_type, from_entity_id,
                           link_type, to_entity_type, to_entity_id)
    return (f"Link created: {from_entity_type}/{from_entity_id[:8]} "
            f"--[{link_type}]--> {to_entity_type}/{to_entity_id[:8]} (id: {lnk.id})")


@mcp.tool()
def get_links(
    entity_type: str,
    entity_id: str,
    direction: str = "both",
) -> str:
    """
    Get all links for an entity.

    Args:
        entity_type: task, decision, note, document, summary.
        entity_id:   UUID of the entity.
        direction:   from, to, or both (default).
    """
    links = _db.get_links_for(entity_type, entity_id, direction)
    if not links:
        return "No links found."
    lines = []
    for lnk in links:
        lines.append(
            f"{lnk.from_entity_type}/{lnk.from_entity_id} "
            f"--[{lnk.link_type}]--> "
            f"{lnk.to_entity_type}/{lnk.to_entity_id}"
        )
    return f"{len(links)} link(s):\n" + "\n".join(lines)


# ── Tags ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def create_tag(project_id: str, name: str) -> str:
    """
    Create a tag for a project.

    Args:
        project_id: Project UUID or name.
        name:       Tag name.
    """
    proj = _db.get_project(project_id)
    if not proj:
        return f"Project '{project_id}' not found."
    tag = _db.create_tag(proj.id, name)
    return f"Tag '{tag.name}' ready (id: {tag.id})"


@mcp.tool()
def tag_entity(
    project_id: str,
    tag_name: str,
    entity_type: str,
    entity_id: str,
) -> str:
    """
    Apply a tag to any entity.

    Args:
        project_id:  Project UUID or name.
        tag_name:    Tag name (will be created if it doesn't exist).
        entity_type: task, decision, note, document.
        entity_id:   UUID of the entity.
    """
    proj = _db.get_project(project_id)
    if not proj:
        return f"Project '{project_id}' not found."
    tag = _db.create_tag(proj.id, tag_name)
    _db.tag_entity(tag.id, entity_type, entity_id)
    return f"Tagged {entity_type}/{entity_id[:8]} with '{tag_name}'"


@mcp.tool()
def list_tags(project_id: str) -> str:
    """
    List all tags for a project.

    Args:
        project_id: Project UUID or name.
    """
    proj = _db.get_project(project_id)
    if not proj:
        return f"Project '{project_id}' not found."
    tags = _db.list_tags(proj.id)
    if not tags:
        return "No tags found."
    return f"{len(tags)} tag(s): " + ", ".join(t.name for t in tags)
