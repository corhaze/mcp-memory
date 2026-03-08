/* components/global-notes.js — Global notes sidebar rendering and logic */

import { els } from '../dom.js';
import { state } from '../state.js';
import { esc } from '../utils.js';

export function renderGlobalNotes(onSelect, onDelete) {
    if (!state.globalNotes.length) {
        els.globalNoteListEl.innerHTML = '<li class="nav-hint" style="font-size:10px;padding:4px 0">No global notes yet.</li>';
        return;
    }
    els.globalNoteListEl.innerHTML = state.globalNotes.map(n => `
        <li class="global-note-item">
          <span class="note-type-pill note-type-${n.note_type}">${n.note_type}</span>
          <button class="global-note-title" data-id="${n.id}">${esc(n.title)}</button>
          <button class="icon-btn danger delete-global-note" data-id="${n.id}">✕</button>
        </li>`).join('');

    els.globalNoteListEl.querySelectorAll('.global-note-title').forEach(btn => {
        btn.addEventListener('click', () => {
            const note = state.globalNotes.find(n => n.id === btn.dataset.id);
            if (note) onSelect(note);
        });
    });
    els.globalNoteListEl.querySelectorAll('.delete-global-note').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            onDelete(btn.dataset.id);
        });
    });
}
