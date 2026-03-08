/* components/search.js — Semantic search coordination and rendering */

import { els } from '../dom.js';
import { state } from '../state.js';
import { renderTaskItem } from './tasks.js';
import { esc } from '../utils.js';

export function renderSearch(handlers = {}) {
    const rs = state.searchResults;
    if (!rs) return;

    const hasTasks = rs.tasks && rs.tasks.length > 0;
    const hasDecisions = rs.decisions && rs.decisions.length > 0;
    const hasNotes = rs.notes && rs.notes.length > 0;

    els.searchTasksList.parentElement.classList.toggle('hidden', !hasTasks);
    els.searchDecisionsList.parentElement.classList.toggle('hidden', !hasDecisions);
    els.searchNotesList.parentElement.classList.toggle('hidden', !hasNotes);

    if (!hasTasks && !hasDecisions && !hasNotes) {
        els.searchEmptyState.classList.remove('hidden');
    } else {
        els.searchEmptyState.classList.add('hidden');
    }

    if (hasTasks) {
        els.searchTasksList.innerHTML = rs.tasks.map(t => renderTaskItem(t, 0)).join('');
        if (handlers.onTasksRender) handlers.onTasksRender(els.searchTasksList);
    }

    if (hasDecisions) {
        els.searchDecisionsList.innerHTML = rs.decisions.map(d => `
        <li class="decision-item ${d.status === 'superseded' ? 'superseded' : ''}">
          <div class="decision-header">
            <span class="decision-title">${esc(d.title)}</span>
            <div class="header-actions">
              <button class="icon-btn edit-decision" data-id="${d.id}">✎</button>
              <button class="icon-btn danger delete-decision" data-id="${d.id}">✗</button>
            </div>
            <span class="status-badge badge-${d.status}">${d.status}</span>
          </div>
          <div class="decision-text">${esc(d.decision_text)}</div>
          ${d.rationale ? `<div class="decision-rationale">${esc(d.rationale)}</div>` : ''}
        </li>
      `).join('');
        if (handlers.onDecisionsRender) handlers.onDecisionsRender(els.searchDecisionsList);
    }

    if (hasNotes) {
        els.searchNotesList.innerHTML = rs.notes.map(n => `
        <li class="note-item">
          <div class="note-header">
            <span class="note-title">${esc(n.title)}</span>
            <div class="header-actions">
              <button class="icon-btn edit-note" data-id="${n.id}">✎</button>
              <button class="icon-btn danger delete-note" data-id="${n.id}">✗</button>
            </div>
            <span class="note-type-pill note-type-${n.note_type}">${n.note_type}</span>
          </div>
          <div class="note-text">${esc(n.note_text)}</div>
        </li>
      `).join('');
        if (handlers.onNotesRender) handlers.onNotesRender(els.searchNotesList);
    }
}
