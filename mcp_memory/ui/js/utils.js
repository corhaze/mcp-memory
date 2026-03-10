/* utils.js — Shared utility functions */

export const STATUS_OPTIONS = ['open', 'in_progress', 'blocked', 'done', 'cancelled'];

export const NOTE_TYPES = ['context', 'investigation', 'implementation', 'bug', 'handover'];

export function renderNoteTypeOptions(current) {
    return NOTE_TYPES.map(t =>
        `<option value="${t}" ${t === current ? 'selected' : ''}>${t}</option>`
    ).join('');
}

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
