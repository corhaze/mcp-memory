/* components/task-detail.js — Task detail page rendering */

import { esc } from '../utils.js';

function renderSubtaskItem(sub) {
    return `<li class="task-detail-subtask">
      <span class="status-badge badge-${esc(sub.status)}">${esc(sub.status)}</span>
      <button class="task-detail-subtask-link task-title-link" data-task-id="${esc(sub.id)}">${esc(sub.title)}</button>
    </li>`;
}

function renderNoteItem(note) {
    return `<li class="task-detail-note">
      <span class="note-type-pill">${esc(note.note_type)}</span>
      <span class="task-detail-note-title">${esc(note.title)}</span>
      <div class="task-detail-note-body">${marked.parse(note.note_text || '')}</div>
    </li>`;
}

function renderEventItem(ev) {
    const note = ev.event_note ? `<span class="task-detail-event-note">${esc(ev.event_note)}</span>` : '';
    return `<li class="task-detail-event">
      <span class="task-detail-event-type">${esc(ev.event_type)}</span>
      ${note}
      <span class="task-detail-event-time">${esc(ev.created_at)}</span>
    </li>`;
}

export function renderTaskDetail(task) {
    const parentLinkHtml = task.parent_task_id
        ? `<div class="task-detail-parent">
             <button class="task-detail-parent-link task-title-link" data-task-id="${esc(task.parent_task_id)}">↑ Parent task</button>
           </div>`
        : '';

    const urgentBadge = task.urgent
        ? `<span class="status-badge badge-urgent">urgent</span>`
        : '';

    const nextActionHtml = task.next_action
        ? `<div class="task-detail-next-action next-action">${esc(task.next_action)}</div>`
        : '';

    const descriptionHtml = task.description
        ? `<div class="task-detail-description markdown-body">${marked.parse(task.description)}</div>`
        : '';

    const subtasksHtml = task.subtasks?.length
        ? `<section class="task-detail-section">
            <h3>Subtasks</h3>
            <ul class="task-detail-subtask-list">${task.subtasks.map(renderSubtaskItem).join('')}</ul>
           </section>`
        : '';

    const notesHtml = task.notes?.length
        ? `<section class="task-detail-section">
            <h3>Notes</h3>
            <ul class="task-detail-notes-list">${task.notes.map(renderNoteItem).join('')}</ul>
           </section>`
        : '';

    const eventsHtml = task.events?.length
        ? `<section class="task-detail-section">
            <h3>Events</h3>
            <ul class="task-detail-events-list">${task.events.map(renderEventItem).join('')}</ul>
           </section>`
        : '';

    return `<div class="task-detail-container">
      <div class="task-detail-nav">
        <button class="task-detail-back btn-secondary">← Back to Tasks</button>
        ${parentLinkHtml}
      </div>
      <header class="task-detail-header">
        <h2 class="task-detail-title">${esc(task.title)}</h2>
        <div class="task-detail-meta">
          <span class="status-badge badge-${esc(task.status)}">${esc(task.status)}</span>
          ${urgentBadge}
          <span class="entity-id-chip" data-full-id="${esc(task.id)}">
            <span class="id-text">${esc(task.id.slice(0, 8))}</span>
          </span>
        </div>
      </header>
      ${descriptionHtml}
      ${nextActionHtml}
      ${subtasksHtml}
      ${notesHtml}
      ${eventsHtml}
    </div>`;
}
