/* components/global-notes.js — Global notes list and expand-in-place editing */

import { renderEntityDetail, bindEntityDetailEvents } from './entity-detail.js';
import { state } from '../state.js';
import { esc } from '../utils.js';

const GLOBAL_NOTE_FIELDS = [
    { name: 'title', label: 'Title', type: 'text', required: true },
    { name: 'note_text', label: 'Note', type: 'textarea', required: true },
    {
        name: 'note_type', label: 'Type', type: 'select', options: [
            { value: 'context', label: 'Context' },
            { value: 'investigation', label: 'Investigation' },
            { value: 'implementation', label: 'Implementation' },
            { value: 'bug', label: 'Bug' },
            { value: 'handover', label: 'Handover' },
        ]
    },
];

export function renderGlobalNotes(options = {}) {
    const listEl = document.getElementById('global-note-list-main');
    if (!listEl) return;

    const notes = state.globalNotes.filter(n => !state.globalNoteFilter || n.note_type === state.globalNoteFilter);

    if (!notes.length) {
        listEl.innerHTML = '<li class="nav-hint">No notes found.</li>';
        return;
    }

    listEl.innerHTML = notes.map(n => {
        const isExpanded = state.expandedGlobalNotes.has(n.id);
        const detailHtml = isExpanded ? renderEntityDetail({
            entityId: n.id,
            entity: n,
            fields: GLOBAL_NOTE_FIELDS
        }) : '';

        return `
        <li class="task-group">
            <div class="task-item">
                <div class="task-header">
                    <button class="task-toggle ${isExpanded ? 'open' : ''}" data-id="${n.id}">▶</button>
                    <div class="task-title-area">
                        <div class="task-title">${esc(n.title)}</div>
                        <div class="task-meta">
                            <span class="note-type-pill note-type-${n.note_type}">${n.note_type}</span>
                        </div>
                    </div>
                </div>
                ${isExpanded ? detailHtml : ''}
            </div>
        </li>`;
    }).join('');

    // Bind toggles
    listEl.querySelectorAll('.task-toggle').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const id = btn.dataset.id;
            if (state.expandedGlobalNotes.has(id)) {
                state.expandedGlobalNotes.delete(id);
            } else {
                state.expandedGlobalNotes.add(id);
            }
            renderGlobalNotes(options);
        });
    });

    // Bind entity detail forms
    notes.forEach(n => {
        if (state.expandedGlobalNotes.has(n.id)) {
            const container = listEl.querySelector(`#entity-detail-${n.id}`);
            if (container) {
                bindEntityDetailEvents(container, {
                    entityId: n.id,
                    onSave: options.onSave,
                    onDelete: options.onDelete,
                    onCollapse: () => {
                        state.expandedGlobalNotes.delete(n.id);
                        renderGlobalNotes(options);
                    }
                });
            }
        }
    });
}
