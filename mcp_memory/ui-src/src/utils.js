/* utils.js — Shared utility functions */

export const STATUS_OPTIONS = ['open', 'in_progress', 'blocked', 'done', 'cancelled'];

export function statusEmoji(status) {
  const map = {
    open: '\u25CB',
    in_progress: '\u25D1',
    blocked: '\u2297',
    done: '\u2713',
    cancelled: '\u2715',
  };
  return map[status] || '\u25CB';
}

/** Build options array for CustomSelect with status colors and emoji. */
export function statusSelectOptions() {
  return STATUS_OPTIONS.map((s) => ({
    value: s,
    label: `${statusEmoji(s)} ${s}`,
    className: `badge-${s}`,
  }));
}

export function formatRelativeTime(isoString) {
  if (!isoString) return '';
  try {
    const d = new Date(isoString);
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
    return isoString.slice(0, 10);
  }
}

export function entityNavTarget(result) {
  const { entity_type, id, project_name, task_id } = result;
  switch (entity_type) {
    case 'task':
      return project_name ? `/${project_name}/tasks/${id}` : null;
    case 'note':
      return project_name ? `/${project_name}/notes/${id}` : null;
    case 'task_note':
      return (project_name && task_id) ? `/${project_name}/tasks/${task_id}` : null;
    case 'global_note':
      return `/global/notes/${id}`;
    case 'decision':
      return project_name ? `/${project_name}/decisions/${id}` : null;
    default:
      return null;
  }
}
