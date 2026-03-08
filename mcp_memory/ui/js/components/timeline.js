/* components/timeline.js — Timeline/event log view rendering */

import { els } from '../dom.js';
import { state } from '../state.js';
import { esc, formatTime } from '../utils.js';

export function renderTimeline() {
    if (!state.timeline.length) {
        els.timelineListEl.innerHTML = '<li class="list-empty">No events yet.</li>';
        return;
    }

    els.timelineListEl.innerHTML = state.timeline.map(ev => `
    <li class="timeline-item">
      <div class="timeline-dot"></div>
      <div class="timeline-content">
        <div class="timeline-event-type">${esc(ev.event_type)}</div>
        <div class="timeline-task-title">${esc(ev.task_title)}</div>
        ${ev.event_note ? `<div class="timeline-note">${esc(ev.event_note)}</div>` : ''}
      </div>
      <div class="timeline-time">${formatTime(ev.created_at)}</div>
    </li>
  `).join('');
}
