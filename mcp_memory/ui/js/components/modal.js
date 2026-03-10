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
    onNoteUpdate,
    onTaskNoteUpdate,
    onGlobalNoteUpdate
}) {
    const form = els.modalBody.querySelector('form');
    if (!form) return;
    const type = form.dataset.type;
    const id = form.dataset.id;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    // Only map empty strings to null for ID fields (e.g., parent_task_id, blocked_by_task_id)
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
        } else if (type === 'note') {
            if (id) await api.patch(`/api/projects/${state.activeProjectId}/notes/${id}`, data);
            else await api.post(`/api/projects/${state.activeProjectId}/notes`, data);
            if (onNoteUpdate) await onNoteUpdate();
        } else if (type === 'task_note') {
            const taskId = form.dataset.taskId;
            await api.post(`/api/tasks/${taskId}/notes`, data);
            if (onTaskNoteUpdate) await onTaskNoteUpdate(taskId);
        } else if (type === 'global_note') {
            const id = form.dataset.id;
            if (id) await api.patch(`/api/global-notes/${id}`, data);
            else await api.post('/api/global-notes', data);
            if (onGlobalNoteUpdate) await onGlobalNoteUpdate();
        }
        hideModal();
    } catch (err) {
        alert(err.message);
    }
}
