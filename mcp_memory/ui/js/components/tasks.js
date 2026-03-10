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

function renderAddSubtaskForm(parentTaskId, taskDepth) {
  const MAX_DEPTH = 5;
  if (taskDepth >= MAX_DEPTH) return '';

  const showForm = state.showAddSubtaskForm.has(parentTaskId);
  const formClass = showForm ? 'add-subtask-form' : 'add-subtask-form hidden';

  return `
    <div class="add-subtask-section" data-parent-id="${parentTaskId}">
      <button class="add-subtask-btn" data-parent-id="${parentTaskId}">+ Add subtask</button>
      <form class="${formClass}" data-parent-id="${parentTaskId}">
        <div class="form-group">
          <label for="subtask-title-${parentTaskId}">Title *</label>
          <input
            type="text"
            id="subtask-title-${parentTaskId}"
            class="subtask-title-input"
            placeholder="Subtask title"
            required
          />
        </div>
        <div class="form-group">
          <label for="subtask-desc-${parentTaskId}">Description</label>
          <textarea
            id="subtask-desc-${parentTaskId}"
            class="subtask-desc-input"
            placeholder="Task description (supports markdown)"
            rows="3"
          ></textarea>
        </div>
        <div class="form-group">
          <label for="subtask-status-${parentTaskId}">Status</label>
          <select id="subtask-status-${parentTaskId}" class="subtask-status-select form-control">
            <option value="open">open</option>
            <option value="in_progress">in_progress</option>
            <option value="blocked">blocked</option>
            <option value="done">done</option>
            <option value="cancelled">cancelled</option>
          </select>
        </div>
        <div class="form-group form-checkbox">
          <input
            type="checkbox"
            id="subtask-urgent-${parentTaskId}"
            class="subtask-urgent-checkbox"
          />
          <label for="subtask-urgent-${parentTaskId}">Urgent</label>
        </div>
        <div class="form-error" id="form-error-${parentTaskId}" style="display:none;"></div>
        <div class="form-actions">
          <button type="submit" class="btn-submit">Submit</button>
          <button type="button" class="btn-cancel" data-parent-id="${parentTaskId}">Cancel</button>
        </div>
      </form>
    </div>`;
}

const STATUS_OPTIONS = ['open', 'in_progress', 'blocked', 'done', 'cancelled'];

function renderStatusOptions(current) {
  return STATUS_OPTIONS.map(s =>
    `<option value="${s}" ${current === s ? 'selected' : ''}>${s}</option>`
  ).join('');
}

function renderNoteTypeOptions(current) {
  const types = ['context', 'investigation', 'implementation', 'bug', 'handover'];
  return types.map(t =>
    `<option value="${t}" ${current === t ? 'selected' : ''}>${t}</option>`
  ).join('');
}

function renderTaskFormFields(task) {
  const isEdit = Boolean(task);
  const v = field => isEdit ? esc(task[field] || '') : '';
  const chk = field => isEdit && task[field] ? 'checked' : '';
  const uid = isEdit ? esc(task.id) : 'new';

  return `
    <div class="form-group">
      <label>Title *</label>
      <input name="title" class="form-control" value="${v('title')}" placeholder="Task title" required>
    </div>
    <div class="form-group">
      <label>Description</label>
      <textarea name="description" class="form-control${isEdit ? ' task-edit-description' : ''}" rows="3" placeholder="Optional description (markdown)">${v('description')}</textarea>
    </div>
    <div class="form-group">
      <label>Status</label>
      <select name="status" class="form-control">${renderStatusOptions(isEdit ? task.status : 'open')}</select>
    </div>
    <div class="form-group form-checkbox">
      <input type="checkbox" name="urgent" id="task-urgent-${uid}" ${chk('urgent')}>
      <label for="task-urgent-${uid}">Urgent</label>
    </div>
    ${isEdit ? `
    <div class="form-group form-checkbox">
      <input type="checkbox" name="complex" id="task-complex-${uid}" ${chk('complex')}>
      <label for="task-complex-${uid}">Complex</label>
    </div>
    <div class="form-group">
      <label>Next Action</label>
      <input name="next_action" class="form-control" value="${v('next_action')}">
    </div>
    <div class="form-group">
      <label>Blocked By Task ID</label>
      <input name="blocked_by_task_id" class="form-control" value="${v('blocked_by_task_id')}">
    </div>` : ''}
    <div class="form-group">
      <label>Assigned Agent</label>
      <input name="assigned_agent" class="form-control" value="${v('assigned_agent')}" placeholder="Optional">
    </div>
    <div class="form-error" style="display:none"></div>`;
}

function renderTaskEditForm(task) {
  const isEditing = state.editingTaskId === task.id;
  return `
    <form class="task-edit-form${isEditing ? '' : ' hidden'}" data-task-id="${esc(task.id)}">
      ${renderTaskFormFields(task)}
      <div class="form-actions">
        <button type="submit" class="btn-submit">Save</button>
        <button type="button" class="btn-cancel btn-cancel-task-edit" data-task-id="${esc(task.id)}">Cancel</button>
      </div>
    </form>`;
}

export function renderAddTopTaskForm() {
  return `
    <form id="add-top-task-form" class="add-subtask-form">
      ${renderTaskFormFields(null)}
      <div class="form-actions">
        <button type="submit" class="btn-submit">Create Task</button>
        <button type="button" class="btn-cancel btn-cancel-top-task">Cancel</button>
      </div>
    </form>`;
}

function renderAddTaskNoteForm(taskId) {
  const showForm = state.showAddTaskNoteForm.has(taskId);
  return `
    <div class="add-task-note-section" data-task-id="${taskId}">
      <form class="add-task-note-form${showForm ? '' : ' hidden'}" data-task-id="${taskId}">
        <div class="form-group">
          <label>Title *</label>
          <input class="note-title-input form-control" placeholder="Note title" required>
        </div>
        <div class="form-group">
          <label>Note</label>
          <textarea class="note-text-input form-control" rows="3" placeholder="Note content (markdown)"></textarea>
        </div>
        <div class="form-group">
          <label>Type</label>
          <select class="note-type-select form-control">
            ${renderNoteTypeOptions('context')}
          </select>
        </div>
        <div class="form-error" style="display:none"></div>
        <div class="form-actions">
          <button type="submit" class="btn-submit">Add Note</button>
          <button type="button" class="btn-cancel btn-cancel-task-note" data-task-id="${taskId}">Cancel</button>
        </div>
      </form>
    </div>`;
}

export function renderTaskItem(task, depth = 0) {
  const MAX_DEPTH = 5;
  const hasSubtasks = task.subtasks && task.subtasks.length > 0;
  const hasDesc = Boolean(task.description);
  const expanded = state.expandedTasks.has(task.id);
  const isEditing = state.editingTaskId === task.id;
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

  const addSubtaskFormHtml = renderAddSubtaskForm(task.id, depth);
  const taskEditFormHtml = renderTaskEditForm(task);
  const addNoteFormHtml = renderAddTaskNoteForm(task.id);

  const bodyHtml = `<div id="task-body-${task.id}" class="task-body${expanded ? '' : ' hidden'}">
             ${taskEditFormHtml}
             <div class="task-view-content${isEditing ? ' hidden' : ''}">
               ${hasDesc ? `<div class="task-description markdown-body">${marked.parse(task.description)}</div>` : ''}
               <div class="task-notes-section">
                 <div class="task-notes-header">
                   <span class="task-notes-label">Notes</span>
                   <button class="add-task-note-btn" data-task-id="${task.id}">+ add note</button>
                 </div>
                 <div id="task-notes-${task.id}">${notesHtml}</div>
                 ${addNoteFormHtml}
               </div>
               ${addSubtaskFormHtml}
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

  const statusDropdownOptions = ['open', 'in_progress', 'blocked', 'done', 'cancelled']
    .map(s => `<div class="status-option badge-${s}" data-value="${s}">${s}</div>`)
    .join('');

  const statusDropdown = `
    <div class="task-status-dropdown" data-task-id="${task.id}">
      <button class="status-badge badge-${task.status} task-status-trigger" data-task-id="${task.id}">${task.status}</button>
      <div class="task-status-options hidden">${statusDropdownOptions}</div>
    </div>`;

  return `
    <li class="task-group" data-depth="${depth}">
      <div class="task-item ${task.status}">
        <div class="task-header">
          ${urgentBadge}
          <div class="task-title-area">
            <div class="task-title">${statusIcon} ${esc(task.title)}</div>
            <div class="task-meta">
              ${complexBadge}
              ${subtaskSummary(task)}
              ${blockedBadge}
              ${task.assigned_agent ? `<span style="font-size:10px;color:var(--text-muted)">[${esc(task.assigned_agent)}]</span>` : ''}
              ${depth === 0 ? `<span class="task-date" title="${task.created_at ? new Date(task.created_at).toLocaleString() : ''}" style="font-size:10px;color:var(--text-dim);margin-left:auto">${formatTime(task.created_at)}</span>` : ''}
            </div>
            ${nextAction}
          </div>
          <div class="header-actions">
            ${statusDropdown}
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
