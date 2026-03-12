/* components/note-detail.js — Note detail page rendering */

import { esc, formatTime } from '../utils.js';

function renderLinkItem(link) {
    const targetType = link.from_entity_type === 'note' || link.from_entity_type === 'global_note'
        ? link.to_entity_type
        : link.from_entity_type;
    const targetId = link.from_entity_type === 'note' || link.from_entity_type === 'global_note'
        ? link.to_entity_id
        : link.from_entity_id;
    const direction = link.from_entity_type === 'note' || link.from_entity_type === 'global_note'
        ? '→'
        : '←';

    return `<li class="note-detail-link">
      <span class="note-detail-link-dir">${direction}</span>
      <span class="note-detail-link-type">${esc(link.link_type)}</span>
      <span class="note-detail-link-target">${esc(targetType)}</span>
      <span class="entity-id-chip" data-full-id="${esc(targetId)}">
        <span class="id-text">${esc(targetId.slice(0, 8))}</span>
      </span>
    </li>`;
}

export function renderNoteDetail(note, { isGlobal = false } = {}) {
    const backLabel = isGlobal ? '← Back to Global Notes' : '← Back to Notes';

    const bodyHtml = note.note_text
        ? `<div class="note-detail-body markdown-body">${marked.parse(note.note_text)}</div>`
        : '';

    const linksHtml = note.links?.length
        ? `<section class="note-detail-section">
            <h3>Linked Entities</h3>
            <ul class="note-detail-link-list">${note.links.map(renderLinkItem).join('')}</ul>
           </section>`
        : '';

    const timestamps = `<div class="note-detail-timestamps">
        <span>Created ${formatTime(note.created_at)}</span>
        <span>Updated ${formatTime(note.updated_at)}</span>
    </div>`;

    return `<div class="note-detail-container">
      <div class="note-detail-nav">
        <button class="note-detail-back btn-secondary">${backLabel}</button>
      </div>
      <header class="note-detail-header">
        <div class="note-detail-title-row">
          <h2 class="note-detail-title">${esc(note.title)}</h2>
          <button class="icon-btn danger delete-note-detail" data-note-id="${esc(note.id)}" title="Delete note">✗</button>
        </div>
        <div class="note-detail-meta">
          ${note.note_type ? `<span class="note-type-pill">${esc(note.note_type)}</span>` : ''}
          <span class="entity-id-chip" data-full-id="${esc(note.id)}">
            <span class="id-text">${esc(note.id.slice(0, 8))}</span>
          </span>
        </div>
      </header>
      ${bodyHtml}
      ${linksHtml}
      ${timestamps}
    </div>`;
}
