/* components/notes.js — Operational notes rendering and logic */

import { els } from '../dom.js';
import { state } from '../state.js';
import { esc, formatTime, renderNoteTypeOptions } from '../utils.js';

function renderNoteEditForm(note) {
    const isEditing = state.editingNoteId === note.id;
    return `
    <form class="note-edit-form${isEditing ? '' : ' hidden'}" data-note-id="${esc(note.id)}">
      <div class="form-group">
        <label>Title</label>
        <input name="title" class="form-control" value="${esc(note.title)}" required>
      </div>
      <div class="form-group">
        <label>Note Text</label>
        <textarea name="note_text" class="form-control note-edit-text">${esc(note.note_text || '')}</textarea>
      </div>
      <div class="form-group">
        <label>Type</label>
        <select name="note_type" class="form-control">${renderNoteTypeOptions(note.note_type)}</select>
      </div>
      <div class="form-error" style="display:none"></div>
      <div class="form-actions">
        <button type="submit" class="btn-submit">Save</button>
        <button type="button" class="btn-cancel btn-cancel-note-edit" data-note-id="${esc(note.id)}">Cancel</button>
      </div>
    </form>`;
}

export function renderNoteItem(n) {
    const isEditing = state.editingNoteId === n.id;
    return `
    <li class="note-item">
      ${renderNoteEditForm(n)}
      <div class="note-view-content${isEditing ? ' hidden' : ''}">
        <div class="note-header">
          <span class="note-title">${esc(n.title)}</span>
          <span class="entity-id-chip" data-full-id="${n.id}" title="Copy ID"><span class="id-text">#${n.id.slice(0, 8)}</span></span>
          <span class="note-date" title="${n.created_at ? new Date(n.created_at).toLocaleString() : ''}" style="font-size:10px;color:var(--text-dim);margin-left:auto;margin-right:10px">${formatTime(n.created_at)}</span>
          <div class="header-actions">
            <button class="icon-btn edit-note" data-id="${n.id}">✎</button>
            <button class="icon-btn danger delete-note" data-id="${n.id}">✗</button>
          </div>
          <span class="note-type-pill note-type-${n.note_type}">${n.note_type}</span>
        </div>
        <div class="note-text markdown-body">${marked.parse(n.note_text)}</div>
      </div>
    </li>`;
}

export function renderNotes() {
    const notes = state.notes || [];
    const filtered = state.noteFilter
        ? notes.filter(n => n.note_type === state.noteFilter)
        : notes;

    if (!filtered.length) {
        els.noteListEl.innerHTML = '<li class="list-empty">No notes found.</li>';
        return;
    }

    els.noteListEl.innerHTML = filtered.map(renderNoteItem).join('');
}
