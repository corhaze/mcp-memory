/* components/modal.js — Modal lifecycle and common form handling */

import { els } from '../dom.js';
import { api } from '../api.js';
import { state } from '../state.js';

export function showModal(title, contentHtml) {
    els.modalTitle.textContent = title;
    els.modalBody.innerHTML = contentHtml;
    els.modalOverlay.classList.remove('hidden');
}

export function hideModal() {
    els.modalOverlay.classList.add('hidden');
    els.modalBody.innerHTML = '';
}

export async function handleModalSave({
    onProjectUpdate,
    onTaskUpdate,
    onDecisionUpdate,
}) {
    const form = els.modalBody.querySelector('form');
    if (!form) return;
    const type = form.dataset.type;
    const id = form.dataset.id;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    // Map empty strings to null for ID fields
    for (const key in data) {
        if (data[key] === '' && key.endsWith('_id')) {
            data[key] = null;
        }
    }

    if (type === 'task') {
        data['urgent'] = !!data['urgent'];
        data['complex'] = !!data['complex'];
    }

    try {
        if (type === 'project') {
            if (id) await api.patch(`/api/projects/${id}`, data);
            else await api.post('/api/projects', data);
            if (onProjectUpdate) await onProjectUpdate(id);
        } else if (type === 'task') {
            if (id) await api.patch(`/api/projects/${state.activeProjectId}/tasks/${id}`, data);
            else await api.post(`/api/projects/${state.activeProjectId}/tasks`, data);
            if (onTaskUpdate) await onTaskUpdate();
        } else if (type === 'decision') {
            if (id) await api.patch(`/api/projects/${state.activeProjectId}/decisions/${id}`, data);
            else await api.post(`/api/projects/${state.activeProjectId}/decisions`, data);
            if (onDecisionUpdate) await onDecisionUpdate();
        }
        hideModal();
    } catch (err) {
        alert(err.message);
    }
}
