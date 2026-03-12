/* utils.js — Shared utility functions */

export const STATUS_OPTIONS = ['open', 'in_progress', 'blocked', 'done', 'cancelled'];

export function renderStatusOptions(current) {
    return STATUS_OPTIONS.map(s =>
        `<option value="${s}" ${s === current ? 'selected' : ''}>${s}</option>`
    ).join('');
}

export function esc(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

export function statusEmoji(status) {
    const map = {
        open: '○',
        in_progress: '◑',
        blocked: '⊗',
        done: '✓',
        cancelled: '✕',
    };
    return map[status] || '○';
}

/**
 * Resolve a search result to a navigation target.
 * Returns { projectName, tab, anchor } or null if the entity type has no target.
 * projectName is null for global_note (use global nav path instead).
 */
export function entityNavTarget(result) {
    const { entity_type, id, project_name, task_id } = result;
    switch (entity_type) {
        case 'task':
            return { projectName: project_name, tab: 'tasks', anchor: `task-${id}` };
        case 'decision':
            return { projectName: project_name, tab: 'decisions', anchor: `decision-${id}` };
        case 'note':
            return { projectName: project_name, tab: 'notes', anchor: `note-${id}` };
        case 'task_note':
            return { projectName: project_name, tab: 'tasks', anchor: `task-${task_id}` };
        case 'global_note':
            return { projectName: null, tab: 'notes', anchor: `global-note-${id}` };
        default:
            return null;
    }
}

export function formatTime(iso) {
    if (!iso) return '';
    try {
        const d = new Date(iso);
        const now = new Date();
        const diffMs = now - d;
        const diffMins = Math.floor(diffMs / 60000);
        if (diffMins < 1) return 'just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours}h ago`;
        const diffDays = Math.floor(diffHours / 24);
        if (diffDays < 7) return `${diffDays}d ago`;
        return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    } catch {
        return iso.slice(0, 10);
    }
}
