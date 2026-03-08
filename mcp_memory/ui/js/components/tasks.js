/* components/tasks.js — Task list rendering and task-specific logic */

import { els } from '../dom.js';
import { state } from '../state.js';
import { api } from '../api.js';
import { esc, statusEmoji, formatTime } from '../utils.js';

export function renderTasks() {
  const filtered = state.taskFilter
    ? state.tasks.filter(t => t.status === state.taskFilter)
    : state.tasks;

  els.taskListEl.dataset.filter = state.taskFilter;

  if (!filtered.length) {
    els.taskListEl.innerHTML = '<li class="list-empty">No tasks found.</li>';
    return;
  }

  els.taskListEl.innerHTML = filtered.map(task => renderTaskItem(task)).join('');
}

function subtaskSummary(task) {
  if (!task.subtasks || task.subtasks.length === 0) return '';
  const total = task.subtasks.length;
  const done = task.subtasks.filter(st => st.status === 'done').length;
  return `<span class="subtask-summary">${done}/${total} completed</span>`;
}

export function renderTaskItem(task, depth = 0) {
  const MAX_DEPTH = 5;
  const hasSubtasks = task.subtasks && task.subtasks.length > 0;
  const hasDesc = Boolean(task.description);
  const expanded = state.expandedTasks.has(task.id);
  const statusIcon = statusEmoji(task.status);

  const blockedBadge = task.blocked_by_task_id
    ? `<span class="blocked-by-badge" title="Blocked by: ${task.blocked_by_task_id}">depends on</span>`
    : '';

  const nextAction = task.next_action
    ? `<div class="task-next-action">${esc(task.next_action)}</div>`
    : '';

  const toggle = `<span class="task-toggle${expanded ? ' open' : ''}" data-task-id="${task.id}" title="Expand">›</span>`;

  const cachedNotes = state.taskNotes[task.id];
  const notesHtml = cachedNotes
    ? renderTaskNotesHtml(task.id, cachedNotes)
    : '<ul class="task-notes-list"><li class="list-empty task-notes-loading" style="font-size:11px;color:var(--text-dim)">—</li></ul>';

  const bodyHtml = `<div id="task-body-${task.id}" class="task-body${expanded ? '' : ' hidden'}">
             ${hasDesc ? `<div class="task-description markdown-body">${marked.parse(task.description)}</div>` : ''}
             <div class="task-notes-section">
               <div class="task-notes-header">
                 <span class="task-notes-label">Notes</span>
                 <button class="add-task-note-btn" data-task-id="${task.id}">+ add note</button>
               </div>
               <div id="task-notes-${task.id}">${notesHtml}</div>
             </div>
           </div>`;

  const subtasksHtml = (hasSubtasks && depth < MAX_DEPTH)
    ? `<ul id="subtasks-${task.id}" class="subtask-list${expanded ? '' : ' hidden'}">
             ${task.subtasks.map(st => renderTaskItem(st, depth + 1)).join('')}
           </ul>`
    : '';

  const urgentBadge = task.urgent
    ? `<span class="urgent-dot" title="Urgent"></span>`
    : '';
  const complexBadge = task.complex
    ? `<span class="complex-badge" title="Complex Task">COMPLEX</span>`
    : '';

  return `
    <li class="task-group" data-depth="${depth}">
      <div class="task-item ${task.status}">
        <div class="task-header">
          ${urgentBadge}
          <div class="task-title-area">
            <div class="task-title">${statusIcon} ${esc(task.title)}</div>
            <div class="task-meta">
              <span class="status-badge badge-${task.status}">${task.status}</span>
              ${complexBadge}
              ${subtaskSummary(task)}
              ${blockedBadge}
              ${task.assigned_agent ? `<span style="font-size:10px;color:var(--text-muted)">[${esc(task.assigned_agent)}]</span>` : ''}
              ${depth === 0 ? `<span class="task-date" title="${task.created_at ? new Date(task.created_at).toLocaleString() : ''}" style="font-size:10px;color:var(--text-dim);margin-left:auto">${formatTime(task.created_at)}</span>` : ''}
            </div>
            ${nextAction}
          </div>
          <div class="header-actions">
            <button class="icon-btn edit-task" data-id="${task.id}">✎</button>
            <button class="icon-btn danger delete-task" data-id="${task.id}">✗</button>
          </div>
          ${toggle}
        </div>
        ${bodyHtml}
      </div>
      ${subtasksHtml}
    </li>`;
}

export function renderTaskNotesHtml(taskId, notes) {
  if (!notes.length) {
    return '<ul class="task-notes-list"><li class="list-empty" style="font-size:11px;color:var(--text-dim)">No notes yet.</li></ul>';
  }
  const items = notes.map(n => `
        <li class="task-note-item">
          <div class="task-note-header">
            <span class="note-type-pill note-type-${n.note_type}">${n.note_type}</span>
            <span class="task-note-title">${esc(n.title)}</span>
            <button class="icon-btn danger delete-task-note" data-note-id="${n.id}" data-task-id="${taskId}">✕</button>
          </div>
          <div class="task-note-text markdown-body">${marked.parse(n.note_text)}</div>
        </li>`).join('');
  return `<ul class="task-notes-list">${items}</ul>`;
}

export function findTask(id, tasks) {
  for (const t of tasks) {
    if (t.id === id) return t;
    if (t.subtasks) {
      const found = findTask(id, t.subtasks);
      if (found) return found;
    }
  }
  return null;
}
