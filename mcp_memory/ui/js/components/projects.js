/* components/projects.js — Project sidebar and navigation */

import { els } from '../dom.js';
import { state } from '../state.js';
import { api } from '../api.js';
import { esc } from '../utils.js';
import { setPath } from '../router.js';

export function renderProjectNav(onSelect) {
    if (!state.projects.length) {
        els.projectList.innerHTML = '<p class="nav-hint">No projects found.</p>';
        return;
    }
    els.projectList.innerHTML = state.projects.map(p => `
    <button class="project-nav-item${state.activeProjectId === p.id ? ' active' : ''}"
            data-id="${p.id}"
            id="proj-nav-${p.id}">
      <span class="proj-dot"></span>
      <span>${esc(p.name)}</span>
    </button>
  `).join('');

    els.projectList.querySelectorAll('.project-nav-item').forEach(btn => {
        btn.addEventListener('click', () => onSelect(btn.dataset.id));
    });
}

export function updateNavHighlight(id) {
    document.querySelectorAll('.project-nav-item').forEach(b => {
        b.classList.toggle('active', b.dataset.id === id);
    });
}

export function showProjectEmptyState() {
    state.activeView = 'empty';
    state.activeProjectId = null;
    els.emptyState.classList.remove('hidden');
    els.projectView.classList.add('hidden');
    if (els.globalView) els.globalView.classList.add('hidden');
    els.searchInput.disabled = true;
    updateNavHighlight(null);
    if (els.globalWorkspaceBtn) els.globalWorkspaceBtn.classList.remove('active');
}

export function renderProjectHeader(proj) {
    els.projectName.textContent = proj.name || state.activeProjectId;
    els.projectDesc.textContent = proj.description || '';
    els.projectStatus.textContent = proj.status || '';
    els.projectStatus.className = `status-badge badge-${proj.status || 'active'}`;
}
