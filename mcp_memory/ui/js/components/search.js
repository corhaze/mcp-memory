/* components/search.js — Semantic search rendering */

import { els } from '../dom.js';
import { state } from '../state.js';
import { esc } from '../utils.js';

function scoreLabel(score) {
    return (score * 100).toFixed(0) + '%';
}

function renderResultItem(result) {
    const { entity_type, score, title, status, note_type, next_action } = result;

    const statusBadge = status
        ? `<span class="status-badge badge-${esc(status)}">${esc(status)}</span>`
        : '';

    const noteTypePill = note_type
        ? `<span class="note-type-pill">${esc(note_type)}</span>`
        : '';

    const nextActionHint = next_action
        ? `<span class="search-result-next-action">${esc(next_action)}</span>`
        : '';

    return `<li class="search-result-item">
      <span class="entity-type-badge badge-${esc(entity_type)}">${esc(entity_type)}</span>
      <span class="search-result-title">${esc(title)}</span>
      ${statusBadge}${noteTypePill}
      <span class="search-result-score">${esc(scoreLabel(score))}</span>
      ${nextActionHint}
    </li>`;
}

export function renderSearch() {
    const rs = state.searchResults;
    if (!rs) return;

    const embeddingsUnavailable = rs.embeddings_available === false;
    if (embeddingsUnavailable) {
        els.searchEmbeddingsNotice.textContent =
            'Semantic search unavailable — keyword search not yet supported in UI.';
        els.searchEmbeddingsNotice.classList.remove('hidden');
    } else {
        els.searchEmbeddingsNotice.classList.add('hidden');
    }

    const results = rs.results ?? [];
    const hasResults = results.length > 0;

    els.searchEmptyState.classList.toggle('hidden', hasResults || embeddingsUnavailable);
    els.searchResultsList.innerHTML = hasResults
        ? results.map(renderResultItem).join('')
        : '';
}
