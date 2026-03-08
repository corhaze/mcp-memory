/* components/modal.js — Modal lifecycle and common form handling */

import { els } from '../dom.js';
import { api } from '../api.js';
import { state } from '../state.js';

export function showModal(title, contentHtml) {
    els.modalTitle.textContent = title;
    els.modalBody.innerHTML = contentHtml;
    initCustomSelects(els.modalBody);
    els.modalOverlay.classList.remove('hidden');
}

export function hideModal() {
    els.modalOverlay.classList.add('hidden');
    els.modalBody.innerHTML = '';
}

export function initCustomSelects(container) {
    container.querySelectorAll('select.form-control').forEach(select => {
        select.style.display = 'none'; // Hide native dropdown

        const wrapper = document.createElement('div');
        wrapper.className = 'custom-select-wrapper';

        const trigger = document.createElement('div');
        trigger.className = 'custom-select-trigger form-control';

        const optionsDiv = document.createElement('div');
        optionsDiv.className = 'custom-select-options hidden';

        const updateTrigger = () => {
            const selectedOpt = select.options[select.selectedIndex];
            trigger.textContent = selectedOpt ? selectedOpt.textContent : '';
        };
        updateTrigger();

        Array.from(select.options).forEach(opt => {
            const optionEl = document.createElement('div');
            optionEl.className = 'custom-select-option';
            optionEl.textContent = opt.textContent;
            optionEl.dataset.value = opt.value;
            if (opt.selected || opt.value === select.value) optionEl.classList.add('selected');

            optionEl.addEventListener('click', (e) => {
                e.stopPropagation();
                select.value = opt.value;
                updateTrigger();
                optionsDiv.classList.add('hidden');
                Array.from(optionsDiv.children).forEach(c => c.classList.remove('selected'));
                optionEl.classList.add('selected');
            });
            optionsDiv.appendChild(optionEl);
        });

        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            const isHidden = optionsDiv.classList.contains('hidden');
            document.querySelectorAll('.custom-select-options').forEach(el => el.classList.add('hidden'));
            if (isHidden) optionsDiv.classList.remove('hidden');
        });

        wrapper.appendChild(trigger);
        wrapper.appendChild(optionsDiv);
        select.parentNode.insertBefore(wrapper, select.nextSibling);
    });
}

// Close custom selects when clicking outside
document.addEventListener('click', () => {
    document.querySelectorAll('.custom-select-options').forEach(el => el.classList.add('hidden'));
});

// handleModalSave is slightly complex because it calls selectProject, loadTaskNotes, loadGlobalNotes etc.
// For now, we will assume these are passed in or we use a circular dependency (not ideal) 
// or simple event-driven architecture.
// Actually, let's keep handleModalSave partially generic or pass the refresh callbacks.

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
