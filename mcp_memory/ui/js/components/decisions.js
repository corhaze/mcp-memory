/* components/decisions.js — Decision list rendering and logic */

import { els } from '../dom.js';
import { state } from '../state.js';
import { esc, formatTime } from '../utils.js';

export function renderDecisionItem(d) {
    return `
    <li id="decision-${d.id}" class="decision-item ${d.status === 'superseded' ? 'superseded' : ''}">
      <div class="decision-header">
        <span class="decision-title">${esc(d.title)}</span>
        <span class="entity-id-chip" data-full-id="${d.id}" title="Copy ID"><span class="id-text">#${d.id.slice(0, 8)}</span></span>
        <div style="margin-left:auto; display:flex; align-items:center; gap:10px;">
          <span class="decision-date" title="${d.created_at ? new Date(d.created_at).toLocaleString() : ''}" style="font-size:10px;color:var(--text-dim)">${formatTime(d.created_at)}</span>
          <span class="status-badge badge-${d.status}">${d.status}</span>
        </div>
        <div class="header-actions">
           <button class="icon-btn edit-decision" data-id="${d.id}">✎</button>
           <button class="icon-btn danger delete-decision" data-id="${d.id}">✗</button>
        </div>
      </div>
      <div class="decision-text markdown-body">${marked.parse(d.decision_text)}</div>
      ${d.rationale ? `<div class="decision-rationale">${esc(d.rationale)}</div>` : ''}
      ${d.supersedes_decision_id ? `<div style="font-size:11px;color:var(--text-muted);margin-top:6px">↳ Supersedes ${d.supersedes_decision_id.slice(0, 8)}</div>` : ''}
    </li>`;
}

export function renderDecisions() {
    const filtered = state.decisionFilter
        ? state.decisions.filter(d => d.status === state.decisionFilter)
        : state.decisions;

    if (!filtered.length) {
        els.decisionListEl.innerHTML = '<li class="list-empty">No decisions found.</li>';
        return;
    }

    els.decisionListEl.innerHTML = filtered.map(renderDecisionItem).join('');
}
