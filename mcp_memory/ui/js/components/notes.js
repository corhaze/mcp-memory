/* components/notes.js — Operational notes rendering and logic */

import { els } from '../dom.js';
import { state } from '../state.js';
import { api } from '../api.js';
import { esc, formatTime } from '../utils.js';

export function renderNotes() {
    const notes = state.notes || [];
    const filtered = state.noteFilter
        ? notes.filter(n => n.note_type === state.noteFilter)
        : notes;

    if (!filtered.length) {
        els.noteListEl.innerHTML = '<li class="list-empty">No notes found.</li>';
        return;
    }

    els.noteListEl.innerHTML = filtered.map(n => `
    <li class="note-item">
      <div class="note-header">
        <span class="note-title">${esc(n.title)}</span>
        <span class="note-date" title="${n.created_at ? new Date(n.created_at).toLocaleString() : ''}" style="font-size:10px;color:var(--text-dim);margin-left:auto;margin-right:10px">${formatTime(n.created_at)}</span>
        <div class="header-actions">
          <button class="icon-btn edit-note" data-id="${n.id}">✎</button>
          <button class="icon-btn danger delete-note" data-id="${n.id}">✗</button>
        </div>
        <span class="note-type-pill note-type-${n.note_type}">${n.note_type}</span>
      </div>
      <div class="note-text markdown-body">${marked.parse(n.note_text)}</div>
    </li>
  `).join('');
}
