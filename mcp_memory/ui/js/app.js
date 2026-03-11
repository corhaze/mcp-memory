/* app.js — Main entry point (initialization and coordination) */

import { els, $ } from './dom.js';
import { state } from './state.js';
import { api } from './api.js';
import { parsePath, setPath, setGlobalPath, setTaskPath, setNotePath, setGlobalNotePath, VALID_TABS } from './router.js';
import { showModal, hideModal, handleModalSave } from './components/modal.js';
import { renderProjectNav, updateNavHighlight, showProjectEmptyState, renderProjectHeader } from './components/projects.js';
import { renderTasks, findTask, renderAddTopTaskForm, renderTaskNotesHtml } from './components/tasks.js';
import { renderDecisions } from './components/decisions.js';
import { renderNotes } from './components/notes.js';
import { renderGlobalNotes } from './components/global-notes.js';
import { renderTimeline } from './components/timeline.js';
import { renderSearch } from './components/search.js';
import { renderKanban, bindKanbanEvents } from './components/kanban.js';

import { esc } from './utils.js';
import { renderTaskDetail, renderSubtaskExpansion } from './components/task-detail.js';
import { renderNoteDetail } from './components/note-detail.js';

// ── Refresh constants ──────────────────────────────────────────────────────────

const STALE_TAB_MS = 30_000;   // refresh on tab switch if data is >30s old
const HIDDEN_STALE_MS = 5_000; // refresh on visibility restore if hidden >5s

// ── Shared Loaders ─────────────────────────────────────────────────────────────

async function loadGlobalNotes() {
    try {
        state.globalNotes = await api.get('/api/global-notes');
        renderGlobalNotes(getGlobalNoteHandlers());
    } catch (err) {
        console.error('Failed to load global notes:', err);
    }
}

function getGlobalNoteHandlers() {
    return {
        onSave: async (id, data) => {
            await api.patch(`/api/global-notes/${id}`, data);
            await loadGlobalNotes();
        },
        onDelete: async (id) => {
            await api.delete(`/api/global-notes/${id}`);
            await loadGlobalNotes();
        }
    };
}

async function selectGlobalWorkspace(tab = 'notes', { updatePath = true } = {}) {
    state.activeView = 'global';
    state.activeProjectId = null;

    document.querySelectorAll('.project-nav-item').forEach(el => el.classList.remove('active'));

    const gwBtn = document.getElementById('global-workspace-btn');
    if (gwBtn) gwBtn.classList.add('active');

    hideAllViews();
    if (els.globalView) els.globalView.classList.remove('hidden');
    els.searchInput.disabled = false;
    els.searchInput.placeholder = 'Search all projects...';

    // "Current project" mode makes no sense without an active project
    const currentBtn = document.querySelector('.toggle-btn[data-mode="current"]');
    const allBtn = document.querySelector('.toggle-btn[data-mode="all"]');
    if (currentBtn) { currentBtn.disabled = true; currentBtn.classList.remove('active'); }
    if (allBtn) { allBtn.disabled = false; allBtn.classList.add('active'); }
    state.searchMode = 'all';

    activateTab('global-notes');

    // Fetch and render to ensure we have latest data
    await loadGlobalNotes();

    if (updatePath) {
        setGlobalPath(tab);
    }
}

function hideAllViews() {
    els.emptyState.classList.add('hidden');
    els.projectView.classList.add('hidden');
    if (els.globalView) els.globalView.classList.add('hidden');
    if (els.taskDetailView) els.taskDetailView.classList.add('hidden');
    if (els.noteDetailView) els.noteDetailView.classList.add('hidden');
}

async function selectTaskDetail(projectName, taskId, { updatePath = true } = {}) {
    state.activeView = 'task-detail';
    state.activeTaskId = taskId;
    state.expandedSubtasks.clear();
    state.subtaskDetails = {};

    // Ensure project data is loaded so nav highlight and back-nav work
    const proj = state.projects.find(p => p.name === projectName);
    if (proj && state.activeProjectId !== proj.id) {
        // Load project data silently so the back button can return to correct tab
        state.activeProjectId = proj.id;
        try {
            const { tasks, decisions, notes, timeline } = await fetchProjectData(proj.id);
            state.tasks = tasks || [];
            state.decisions = decisions || [];
            state.notes = notes || [];
            state.timeline = timeline || [];
        } catch { /* silent */ }
    }

    updateNavHighlight(proj?.id ?? null);
    els.globalWorkspaceBtn?.classList.remove('active');

    hideAllViews();
    if (els.taskDetailView) els.taskDetailView.classList.remove('hidden');

    try {
        const task = await api.get(`/api/projects/${proj?.id ?? projectName}/tasks/${taskId}`);
        if (els.taskDetailContent) {
            els.taskDetailContent.innerHTML = renderTaskDetail(task);
        }
        if (updatePath) setTaskPath(projectName, taskId);
    } catch (err) {
        if (els.taskDetailContent) {
            els.taskDetailContent.innerHTML = `<p class="nav-hint">Failed to load task: ${esc(err.message)}</p>`;
        }
    }
}

async function selectNoteDetail(projectName, noteId, { isGlobal = false, updatePath = true } = {}) {
    state.activeView = 'note-detail';
    state.activeNoteId = noteId;

    if (!isGlobal) {
        const proj = state.projects.find(p => p.name === projectName);
        if (proj && state.activeProjectId !== proj.id) {
            state.activeProjectId = proj.id;
            try {
                const { tasks, decisions, notes, timeline } = await fetchProjectData(proj.id);
                state.tasks = tasks || [];
                state.decisions = decisions || [];
                state.notes = notes || [];
                state.timeline = timeline || [];
            } catch { /* silent */ }
        }
        updateNavHighlight(proj?.id ?? null);
        els.globalWorkspaceBtn?.classList.remove('active');
    } else {
        state.activeProjectId = null;
        document.querySelectorAll('.project-nav-item').forEach(el => el.classList.remove('active'));
        const gwBtn = document.getElementById('global-workspace-btn');
        if (gwBtn) gwBtn.classList.add('active');
    }

    hideAllViews();
    if (els.noteDetailView) els.noteDetailView.classList.remove('hidden');

    try {
        const url = isGlobal
            ? `/api/global-notes/${noteId}`
            : `/api/projects/${state.activeProjectId ?? projectName}/notes/${noteId}`;
        const note = await api.get(url);
        if (els.noteDetailContent) {
            els.noteDetailContent.innerHTML = renderNoteDetail(note, { isGlobal });
        }
        if (updatePath) {
            if (isGlobal) {
                setGlobalNotePath(noteId);
            } else {
                setNotePath(projectName, noteId);
            }
        }
    } catch (err) {
        if (els.noteDetailContent) {
            els.noteDetailContent.innerHTML = `<p class="nav-hint">Failed to load note: ${esc(err.message)}</p>`;
        }
    }
}

async function loadTaskNotes(taskId) {
    try {
        const notes = await api.get(`/api/tasks/${taskId}/notes`);
        state.taskNotes[taskId] = notes;
        const container = document.getElementById(`task-notes-${taskId}`);
        if (container) {
            container.innerHTML = renderTaskNotesHtml(taskId, notes);
            bindTaskNoteButtons(taskId);
        }
    } catch (err) {
        console.error('Failed to load task notes:', err);
    }
}

function bindTaskNoteButtons(taskId) {
    const container = document.getElementById(`task-notes-${taskId}`);
    if (!container) return;
    container.querySelectorAll('.delete-task-note').forEach(btn => {
        btn.addEventListener('click', e => {
            e.stopPropagation();
            deleteTaskNote(btn.dataset.noteId, btn.dataset.taskId);
        });
    });
}

async function deleteTaskNote(noteId, taskId) {
    if (!confirm('Delete this note?')) return;
    try {
        await api.delete(`/api/task-notes/${noteId}`);
        delete state.taskNotes[taskId];
        await loadTaskNotes(taskId);
    } catch (err) {
        alert(err.message);
    }
}

async function submitTaskEditForm(form) {
    const taskId = form.dataset.taskId;
    const errorDiv = form.querySelector('.form-error');
    errorDiv.style.display = 'none';

    const title = form.querySelector('[name="title"]').value.trim();
    if (!title) {
        errorDiv.textContent = 'Title is required';
        errorDiv.style.display = 'block';
        return;
    }

    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    // FormData omits unchecked checkboxes — handle explicitly
    data.urgent = form.querySelector('[name="urgent"]').checked;
    data.complex = form.querySelector('[name="complex"]').checked;
    // Map empty ID fields to null
    for (const key of ['parent_task_id', 'blocked_by_task_id']) {
        if (data[key] === '') data[key] = null;
    }

    const submitBtn = form.querySelector('.btn-submit');
    submitBtn.textContent = 'Saving…';
    submitBtn.disabled = true;

    try {
        await api.patch(`/api/projects/${state.activeProjectId}/tasks/${taskId}`, data);
        state.editingTaskId = null;
        await refreshTasks();
    } catch (err) {
        errorDiv.textContent = err.message || 'Failed to save';
        errorDiv.style.display = 'block';
        submitBtn.textContent = 'Save';
        submitBtn.disabled = false;
    }
}

async function submitAddTaskNoteForm(form) {
    const taskId = form.dataset.taskId;
    const errorDiv = form.querySelector('.form-error');
    errorDiv.style.display = 'none';

    const title = form.querySelector('.note-title-input').value.trim();
    const noteText = form.querySelector('.note-text-input').value.trim();
    const noteType = form.querySelector('.note-type-select').value;

    if (!title) {
        errorDiv.textContent = 'Title is required';
        errorDiv.style.display = 'block';
        return;
    }

    const submitBtn = form.querySelector('.btn-submit');
    submitBtn.textContent = 'Saving…';
    submitBtn.disabled = true;

    try {
        await api.post(`/api/tasks/${taskId}/notes`, { title, note_text: noteText, note_type: noteType });
        state.showAddTaskNoteForm.delete(taskId);
        await loadTaskNotes(taskId);
    } catch (err) {
        errorDiv.textContent = err.message || 'Failed to add note';
        errorDiv.style.display = 'block';
        submitBtn.textContent = 'Add Note';
        submitBtn.disabled = false;
    }
}

function showAddTopTaskForm() {
    state.showAddTaskForm = true;
    els.addTaskFormContainer.innerHTML = renderAddTopTaskForm();
    els.addTaskFormContainer.classList.remove('hidden');
    els.addTaskFormContainer.querySelector('[name="title"]')?.focus();

    const form = els.addTaskFormContainer.querySelector('#add-top-task-form');

    form.querySelector('.btn-submit').addEventListener('click', async e => {
        e.preventDefault();
        const errorDiv = form.querySelector('.form-error');
        errorDiv.style.display = 'none';

        const title = form.querySelector('[name="title"]').value.trim();
        if (!title) {
            errorDiv.textContent = 'Title is required';
            errorDiv.style.display = 'block';
            return;
        }

        const description = form.querySelector('[name="description"]').value.trim() || null;
        const status = form.querySelector('[name="status"]').value;
        const urgent = form.querySelector('[name="urgent"]').checked;
        const assigned_agent = form.querySelector('[name="assigned_agent"]').value.trim() || null;

        const submitBtn = form.querySelector('.btn-submit');
        submitBtn.textContent = 'Creating…';
        submitBtn.disabled = true;

        try {
            await api.post(`/api/projects/${state.activeProjectId}/tasks`, {
                title, description, status, urgent, assigned_agent
            });
            state.showAddTaskForm = false;
            els.addTaskFormContainer.classList.add('hidden');
            els.addTaskFormContainer.innerHTML = '';
            await refreshTasks();
        } catch (err) {
            errorDiv.textContent = err.message || 'Failed to create task';
            errorDiv.style.display = 'block';
            submitBtn.textContent = 'Create Task';
            submitBtn.disabled = false;
        }
    });

    form.querySelector('.btn-cancel-top-task').addEventListener('click', () => {
        state.showAddTaskForm = false;
        els.addTaskFormContainer.classList.add('hidden');
        els.addTaskFormContainer.innerHTML = '';
    });
}

// ── Refresh helpers ───────────────────────────────────────────────────────────

function showRefreshIndicator() {
    const el = document.getElementById('refresh-indicator');
    if (!el) return;
    el.classList.remove('active');
    void el.offsetWidth; // force reflow to restart animation
    el.classList.add('active');
}

function isDataStale(thresholdMs) {
    return !state.lastFetchedAt || (Date.now() - state.lastFetchedAt) > thresholdMs;
}

async function fetchProjectData(id) {
    const [ctx, tasks, decisions, notes, timeline] = await Promise.all([
        api.get(`/api/projects/${id}`),
        api.get(`/api/projects/${id}/tasks?topo=true`),
        api.get(`/api/projects/${id}/decisions`),
        api.get(`/api/projects/${id}/notes`),
        api.get(`/api/projects/${id}/timeline`),
    ]);
    return { ctx, tasks, decisions, notes, timeline };
}

async function refreshProjectData() {
    if (!state.activeProjectId) return;
    showRefreshIndicator();
    try {
        const { ctx, tasks, decisions, notes, timeline } = await fetchProjectData(state.activeProjectId);
        state.tasks = tasks || [];
        state.decisions = decisions || [];
        state.notes = notes || [];
        state.timeline = timeline || [];
        state.lastFetchedAt = Date.now();
        // Re-render panels without resetting expanded state or active tab
        renderTasks();
        renderKanban();
        renderDecisions();
        renderNotes();
        renderTimeline();
    } catch {
        // silent — don't disrupt UX on background refresh failure
    }
}

async function refreshTasks() {
    if (!state.activeProjectId) return;
    state.tasks = await api.get(`/api/projects/${state.activeProjectId}/tasks?topo=true`);
    renderTasks();
    renderKanban();
}

async function refreshDecisions() {
    if (!state.activeProjectId) return;
    state.decisions = await api.get(`/api/projects/${state.activeProjectId}/decisions`);
    renderDecisions();
}

async function refreshNotes() {
    if (!state.activeProjectId) return;
    state.notes = await api.get(`/api/projects/${state.activeProjectId}/notes`);
    renderNotes();
}

// ── Project Selection ─────────────────────────────────────────────────────────

async function selectProject(id, tab = 'summary', { updatePath = true } = {}) {
    state.activeProjectId = id;
    state.activeView = 'project';
    state.expandedTasks.clear();

    updateNavHighlight(id);
    els.globalWorkspaceBtn?.classList.remove('active');

    hideAllViews();
    els.projectView.classList.remove('hidden');
    els.searchInput.disabled = false;

    // Restore both search mode toggles
    document.querySelectorAll('.toggle-btn').forEach(b => b.disabled = false);

    showRefreshIndicator();
    try {
        const { ctx, tasks, decisions, notes, timeline } = await fetchProjectData(id);
        state.tasks = tasks || [];
        state.decisions = decisions || [];
        state.notes = notes || [];
        state.timeline = timeline || [];
        state.lastFetchedAt = Date.now();
        renderProjectView(ctx, tab, updatePath);
    } catch (err) {
        alert("Failed to load project: " + err.message);
    }
}

function renderProjectView(ctx, tab = 'summary', updatePath = true) {
    const id = state.activeProjectId;
    const proj = ctx.project || {};

    renderProjectHeader(proj);

    bindSummaryInlineEditor(ctx.summary || '');

    renderTasks();
    renderKanban();
    renderDecisions();
    renderNotes();
    renderTimeline();

    activateTab(tab);

    if (updatePath) {
        const projItem = state.projects.find(p => p.id === id);
        if (projItem) setPath(projItem.name, tab);
    }
}

// ── UI Coordination ───────────────────────────────────────────────────────────

function getActiveTab() {
    return document.querySelector('.tab.active')?.dataset.tab || 'summary';
}

function activateTab(name) {
    document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
    document.querySelectorAll('.panel').forEach(p => p.classList.toggle('hidden', p.id !== `panel-${name}`));
}

function bindTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const name = tab.dataset.tab;
            activateTab(name);
            if (state.activeProjectId) {
                const proj = state.projects.find(p => p.id === state.activeProjectId);
                if (proj) setPath(proj.name, name, true);
                if (isDataStale(STALE_TAB_MS)) refreshProjectData();
            }
        });
    });
}

function bindFilters() {
    els.taskFilters.addEventListener('click', e => {
        const btn = e.target.closest('.filter-btn');
        if (!btn) return;
        els.taskFilters.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.taskFilter = btn.dataset.status;
        els.taskListEl.dataset.filter = btn.dataset.status;
        renderTasks();
    });

    els.decisionFilters.addEventListener('click', e => {
        const btn = e.target.closest('.filter-btn');
        if (!btn) return;
        els.decisionFilters.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.decisionFilter = btn.dataset.status;
        renderDecisions();
    });

    els.noteFilters.addEventListener('click', e => {
        const btn = e.target.closest('.filter-btn');
        if (!btn) return;
        els.noteFilters.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.noteFilter = btn.dataset.type;
        renderNotes();
    });
}

// ── Search ─────────────────────────────────────────────────────────────────────

async function performSearch(query) {
    try {
        const url = state.activeProjectId
            ? `/api/projects/${state.activeProjectId}/search/semantic?q=${encodeURIComponent(query)}`
            : `/api/search/semantic?q=${encodeURIComponent(query)}`;
        const data = await api.get(url);
        state.searchResults = data;
        // Show the project-view shell to render the search panel even without a project
        if (!state.activeProjectId) {
            hideAllViews();
            els.projectView.classList.remove('hidden');
        }
        els.searchTab.classList.remove('hidden');
        activateTab('search');
        renderSearch();
    } catch (err) {
        alert(err.message);
    }
}

// ── Event Bindings ────────────────────────────────────────────────────────────

function handleTaskToggle(e, btn) {
    e.stopPropagation();
    const id = btn.dataset.taskId;
    const isExpanded = state.expandedTasks.has(id);
    if (isExpanded) state.expandedTasks.delete(id);
    else state.expandedTasks.add(id);

    const nowExpanded = !isExpanded;
    const taskGroup = btn.closest('.task-group');
    const taskItem = btn.closest('.task-item');
    const body = taskItem ? taskItem.querySelector('.task-body') : null;
    const subs = taskGroup ? taskGroup.querySelector('.subtask-list') : null;

    if (body) body.classList.toggle('hidden', !nowExpanded);
    if (subs) subs.classList.toggle('hidden', !nowExpanded);
    btn.classList.toggle('open', nowExpanded);
    if (nowExpanded && !state.taskNotes[id]) loadTaskNotes(id);
}

// ── Add Subtask Form Handlers ─────────────────────────────────────────────

function toggleAddSubtaskForm(btn) {
    const parentTaskId = btn.dataset.parentId;
    const section = btn.closest('.add-subtask-section');
    const form = section.querySelector('.add-subtask-form');

    const isCurrentlyShown = state.showAddSubtaskForm.has(parentTaskId);

    if (isCurrentlyShown) {
        // Close form
        state.showAddSubtaskForm.delete(parentTaskId);
        form.classList.add('hidden');
        btn.textContent = '+ Add subtask';
    } else {
        // Open form
        state.showAddSubtaskForm.add(parentTaskId);
        form.classList.remove('hidden');
        btn.textContent = '− Close form';
        // Focus the title input for better UX
        const titleInput = form.querySelector('.subtask-title-input');
        if (titleInput) titleInput.focus();
    }
}

async function submitAddSubtaskForm(form) {
    const parentTaskId = form.dataset.parentId;
    const errorDiv = form.querySelector('.form-error');

    // Clear previous error
    errorDiv.style.display = 'none';
    errorDiv.textContent = '';

    // Get form values and trim
    const title = form.querySelector('.subtask-title-input').value.trim();
    const description = form.querySelector('.subtask-desc-input').value.trim();
    const status = form.querySelector('.subtask-status-select').value;
    const urgent = form.querySelector('.subtask-urgent-checkbox').checked;

    // Validate title
    if (!title) {
        errorDiv.textContent = 'Title is required';
        errorDiv.style.display = 'block';
        return;
    }

    // Get parent task to extract project_id
    const parentTask = findTask(parentTaskId, state.tasks);
    if (!parentTask) {
        errorDiv.textContent = 'Parent task not found';
        errorDiv.style.display = 'block';
        return;
    }

    try {
        // Create the subtask
        await api.post(`/api/projects/${parentTask.project_id}/tasks`, {
            title,
            description: description || null,
            status,
            urgent,
            parent_task_id: parentTaskId
        });

        // Close form and clear inputs
        state.showAddSubtaskForm.delete(parentTaskId);
        form.classList.add('hidden');
        form.querySelector('.subtask-title-input').value = '';
        form.querySelector('.subtask-desc-input').value = '';
        form.querySelector('.subtask-status-select').value = 'open';
        form.querySelector('.subtask-urgent-checkbox').checked = false;

        // Reset button text
        const btn = form.closest('.add-subtask-section').querySelector('.add-subtask-btn');
        if (btn) btn.textContent = '+ Add subtask';

        await refreshTasks();
    } catch (err) {
        errorDiv.textContent = err.message || 'Failed to create subtask';
        errorDiv.style.display = 'block';
    }
}

function cancelAddSubtaskForm(btn) {
    const form = btn.closest('.add-subtask-form');
    const parentTaskId = form.dataset.parentId;
    const section = form.closest('.add-subtask-section');
    const toggleBtn = section.querySelector('.add-subtask-btn');

    // Remove from state
    state.showAddSubtaskForm.delete(parentTaskId);

    // Hide form and reset button text
    form.classList.add('hidden');
    if (toggleBtn) toggleBtn.textContent = '+ Add subtask';

    // Clear all inputs
    form.querySelector('.subtask-title-input').value = '';
    form.querySelector('.subtask-desc-input').value = '';
    form.querySelector('.subtask-status-select').value = 'open';
    form.querySelector('.subtask-urgent-checkbox').checked = false;

    // Clear error message
    const errorDiv = form.querySelector('.form-error');
    if (errorDiv) {
        errorDiv.textContent = '';
        errorDiv.style.display = 'none';
    }
}

// ── Delegated event handlers (bound once in init) ───────────────────────────

function bindTaskDetailEvents() {
    if (!els.taskDetailContent) return;
    els.taskDetailContent.addEventListener('click', async e => {
        const backBtn = e.target.closest('.task-detail-back');
        if (backBtn) {
            const proj = state.projects.find(p => p.id === state.activeProjectId);
            if (proj) selectProject(proj.id, 'tasks');
            return;
        }

        const expandToggle = e.target.closest('.subtask-expand-toggle');
        if (expandToggle) {
            e.stopPropagation();
            const subtaskId = expandToggle.dataset.subtaskId;
            const container = document.getElementById(`subtask-expansion-${subtaskId}`);
            if (!container) return;

            const isExpanded = state.expandedSubtasks.has(subtaskId);
            if (isExpanded) {
                state.expandedSubtasks.delete(subtaskId);
                container.classList.add('hidden');
                expandToggle.classList.remove('open');
            } else {
                state.expandedSubtasks.add(subtaskId);
                expandToggle.classList.add('open');
                if (!state.subtaskDetails[subtaskId]) {
                    container.innerHTML = '<p class="nav-hint" style="padding:0.5rem">Loading…</p>';
                    container.classList.remove('hidden');
                    try {
                        state.subtaskDetails[subtaskId] = await api.get(
                            `/api/projects/${state.activeProjectId}/tasks/${subtaskId}`
                        );
                    } catch {
                        container.innerHTML = '<p class="nav-hint" style="padding:0.5rem">Failed to load.</p>';
                        return;
                    }
                }
                container.innerHTML = renderSubtaskExpansion(state.subtaskDetails[subtaskId]);
                container.classList.remove('hidden');
            }
            return;
        }

        const deleteTaskBtn = e.target.closest('.delete-task-detail');
        if (deleteTaskBtn) {
            const taskId = deleteTaskBtn.dataset.taskId;
            if (!confirm('Delete this task?')) return;
            try {
                await api.delete(`/api/projects/${state.activeProjectId}/tasks/${taskId}`);
                const proj = state.projects.find(p => p.id === state.activeProjectId);
                if (proj) selectProject(proj.id, 'tasks');
            } catch (err) { alert(err.message); }
            return;
        }

        const deleteSubtaskBtn = e.target.closest('.delete-subtask-detail');
        if (deleteSubtaskBtn) {
            const taskId = deleteSubtaskBtn.dataset.taskId;
            if (!confirm('Delete this subtask?')) return;
            try {
                await api.delete(`/api/projects/${state.activeProjectId}/tasks/${taskId}`);
                // Reload the current task detail to reflect the removed subtask
                const proj = state.projects.find(p => p.id === state.activeProjectId);
                if (proj) selectTaskDetail(proj.name, state.activeTaskId, { updatePath: false });
            } catch (err) { alert(err.message); }
            return;
        }

        const taskLink = e.target.closest('.task-detail-subtask-link, .task-detail-parent-link');
        if (taskLink) {
            const taskId = taskLink.dataset.taskId;
            const proj = state.projects.find(p => p.id === state.activeProjectId);
            if (proj && taskId) selectTaskDetail(proj.name, taskId);
        }
    });
}

function bindNoteDetailEvents() {
    if (!els.noteDetailContent) return;
    els.noteDetailContent.addEventListener('click', async e => {
        const backBtn = e.target.closest('.note-detail-back');
        if (backBtn) {
            if (state.activeProjectId) {
                const proj = state.projects.find(p => p.id === state.activeProjectId);
                if (proj) selectProject(proj.id, 'notes');
            } else {
                await selectGlobalWorkspace('notes');
            }
            return;
        }

        const deleteBtn = e.target.closest('.delete-note-detail');
        if (deleteBtn) {
            const noteId = deleteBtn.dataset.noteId;
            if (!confirm('Delete this note?')) return;
            try {
                if (state.activeProjectId) {
                    await api.delete(`/api/projects/${state.activeProjectId}/notes/${noteId}`);
                    const proj = state.projects.find(p => p.id === state.activeProjectId);
                    if (proj) selectProject(proj.id, 'notes');
                } else {
                    await api.delete(`/api/global-notes/${noteId}`);
                    await selectGlobalWorkspace('notes');
                }
            } catch (err) { alert(err.message); }
        }
    });
}

function bindTaskListEvents() {
    els.taskListEl.addEventListener('click', async e => {
        const statusTrigger = e.target.closest('.task-status-trigger');
        if (statusTrigger) {
            e.stopPropagation();
            const dropdown = statusTrigger.closest('.task-status-dropdown');
            const options = dropdown.querySelector('.task-status-options');
            const isOpen = !options.classList.contains('hidden');
            document.querySelectorAll('.task-status-options').forEach(o => o.classList.add('hidden'));
            if (!isOpen) options.classList.remove('hidden');
            return;
        }

        const statusOption = e.target.closest('.task-status-options .status-option');
        if (statusOption) {
            e.stopPropagation();
            const dropdown = statusOption.closest('.task-status-dropdown');
            const taskId = dropdown.dataset.taskId;
            const newStatus = statusOption.dataset.value;
            dropdown.querySelector('.task-status-options').classList.add('hidden');
            try {
                await api.patch(`/api/projects/${state.activeProjectId}/tasks/${taskId}`, { status: newStatus });
                await refreshTasks();
            } catch (err) {
                alert(err.message);
            }
            return;
        }

        const taskTitleLink = e.target.closest('.task-title-link');
        if (taskTitleLink) {
            e.stopPropagation();
            const taskId = taskTitleLink.dataset.taskId;
            const proj = state.projects.find(p => p.id === state.activeProjectId);
            if (proj) selectTaskDetail(proj.name, taskId);
            return;
        }

        const taskToggle = e.target.closest('.task-toggle');
        if (taskToggle) {
            handleTaskToggle(e, taskToggle);
            return;
        }

        const addNoteBtn = e.target.closest('.add-task-note-btn');
        if (addNoteBtn) {
            e.stopPropagation();
            const taskId = addNoteBtn.dataset.taskId;
            const section = els.taskListEl.querySelector(`.add-task-note-section[data-task-id="${taskId}"]`);
            if (!section) return;
            const form = section.querySelector('.add-task-note-form');
            if (!form) return;
            const isOpen = state.showAddTaskNoteForm.has(taskId);
            if (isOpen) {
                state.showAddTaskNoteForm.delete(taskId);
                form.classList.add('hidden');
            } else {
                state.showAddTaskNoteForm.add(taskId);
                form.classList.remove('hidden');
                form.querySelector('.note-title-input')?.focus();
            }
            return;
        }

        const cancelNoteBtn = e.target.closest('.btn-cancel-task-note');
        if (cancelNoteBtn) {
            e.stopPropagation();
            const form = cancelNoteBtn.closest('.add-task-note-form');
            state.showAddTaskNoteForm.delete(form.dataset.taskId);
            form.classList.add('hidden');
            form.reset();
            return;
        }

        const submitNoteBtn = e.target.closest('.add-task-note-form .btn-submit');
        if (submitNoteBtn) {
            e.preventDefault();
            e.stopPropagation();
            await submitAddTaskNoteForm(submitNoteBtn.closest('.add-task-note-form'));
            return;
        }

        const editTaskBtn = e.target.closest('.edit-task');
        if (editTaskBtn) {
            e.stopPropagation();
            const taskId = editTaskBtn.dataset.id;
            state.editingTaskId = state.editingTaskId === taskId ? null : taskId;
            if (state.editingTaskId) state.expandedTasks.add(taskId);
            renderTasks();
            return;
        }

        const cancelEditBtn = e.target.closest('.btn-cancel-task-edit');
        if (cancelEditBtn) {
            e.stopPropagation();
            state.editingTaskId = null;
            renderTasks();
            return;
        }

        const deleteTaskBtn = e.target.closest('.delete-task');
        if (deleteTaskBtn) {
            e.stopPropagation();
            deleteTask(deleteTaskBtn.dataset.id);
            return;
        }

        const addSubtaskBtn = e.target.closest('.add-subtask-btn');
        if (addSubtaskBtn) {
            e.stopPropagation();
            toggleAddSubtaskForm(addSubtaskBtn);
            return;
        }

        const submitSubtaskBtn = e.target.closest('.add-subtask-form .btn-submit');
        if (submitSubtaskBtn) {
            e.preventDefault();
            e.stopPropagation();
            await submitAddSubtaskForm(submitSubtaskBtn.closest('.add-subtask-form'));
            return;
        }

        // Subtask cancel (exclude more-specific cancel buttons)
        const cancelSubtaskBtn = e.target.closest(
            '.btn-cancel:not(.btn-cancel-task-edit):not(.btn-cancel-task-note)'
        );
        if (cancelSubtaskBtn && els.taskListEl.contains(cancelSubtaskBtn)) {
            e.preventDefault();
            e.stopPropagation();
            cancelAddSubtaskForm(cancelSubtaskBtn);
        }
    });

    els.taskListEl.addEventListener('submit', async e => {
        const form = e.target.closest('.task-edit-form');
        if (form) {
            e.preventDefault();
            e.stopPropagation();
            await submitTaskEditForm(form);
        }
    });
}

function bindDecisionListEvents() {
    els.decisionListEl.addEventListener('click', e => {
        const editBtn = e.target.closest('.edit-decision');
        if (editBtn) {
            const dec = state.decisions.find(d => d.id === editBtn.dataset.id);
            if (dec) showDecisionForm(dec);
            return;
        }
        const deleteBtn = e.target.closest('.delete-decision');
        if (deleteBtn) {
            deleteDecision(deleteBtn.dataset.id);
        }
    });
}

async function submitNoteEditForm(form) {
    const noteId = form.dataset.noteId;
    const errorDiv = form.querySelector('.form-error');
    errorDiv.style.display = 'none';

    const title = form.querySelector('[name="title"]').value.trim();
    if (!title) {
        errorDiv.textContent = 'Title is required';
        errorDiv.style.display = 'block';
        return;
    }

    const data = {
        title,
        note_text: form.querySelector('[name="note_text"]').value.trim(),
        note_type: form.querySelector('[name="note_type"]').value,
    };

    const submitBtn = form.querySelector('.btn-submit');
    submitBtn.textContent = 'Saving…';
    submitBtn.disabled = true;

    try {
        await api.patch(`/api/projects/${state.activeProjectId}/notes/${noteId}`, data);
        state.editingNoteId = null;
        await refreshNotes();
    } catch (err) {
        errorDiv.textContent = err.message || 'Failed to save';
        errorDiv.style.display = 'block';
        submitBtn.textContent = 'Save';
        submitBtn.disabled = false;
    }
}

function bindNoteListEvents() {
    els.noteListEl.addEventListener('click', e => {
        const toggleBtn = e.target.closest('.note-item .task-toggle');
        if (toggleBtn) {
            e.stopPropagation();
            const id = toggleBtn.dataset.id;
            if (state.expandedNotes.has(id)) {
                state.expandedNotes.delete(id);
            } else {
                state.expandedNotes.add(id);
            }
            renderNotes();
            return;
        }
        const editBtn = e.target.closest('.edit-note');
        if (editBtn) {
            const noteId = editBtn.dataset.id;
            state.expandedNotes.add(noteId); // ensure expanded when editing
            state.editingNoteId = state.editingNoteId === noteId ? null : noteId;
            renderNotes();
            return;
        }
        const cancelBtn = e.target.closest('.btn-cancel-note-edit');
        if (cancelBtn) {
            state.editingNoteId = null;
            renderNotes();
            return;
        }
        const deleteBtn = e.target.closest('.delete-note');
        if (deleteBtn) {
            deleteNote(deleteBtn.dataset.id);
        }
    });

    els.noteListEl.addEventListener('submit', async e => {
        const form = e.target.closest('.note-edit-form');
        if (form) {
            e.preventDefault();
            await submitNoteEditForm(form);
        }
    });
}

// ── Forms & CRUD (Proxy to modal handlers) ──────────────────────────────────

function showProjectForm(proj = null) {
    const html = `
    <form data-type="project" data-id="${proj ? proj.id : ''}">
        <div class="form-group"><label>Name</label><input name="name" class="form-control" value="${proj ? esc(proj.name) : ''}" required ${proj ? 'readonly' : ''}></div>
        <div class="form-group"><label>Description</label><textarea name="description" class="form-control">${proj ? esc(proj.description) : ''}</textarea></div>
        <div class="form-group"><label>Status</label><select name="status" class="form-control">
            <option value="active" ${proj?.status === 'active' ? 'selected' : ''}>Active</option>
            <option value="archived" ${proj?.status === 'archived' ? 'selected' : ''}>Archived</option>
        </select></div>
    </form>`;
    showModal(proj ? 'Edit Project' : 'New Project', html);
}


function bindSummaryInlineEditor(summaryText) {
    els.projectSummary.innerHTML = `
        <div class="summary-view">
            <div class="summary-toolbar">
                <button class="btn-secondary btn-edit-summary">✎ Edit</button>
            </div>
            <div class="markdown-body">${summaryText ? marked.parse(summaryText) : '<p class="nav-hint">No project summary yet.</p>'}</div>
        </div>
        <form class="summary-form hidden">
            <div class="summary-toolbar">
                <button type="button" class="btn-secondary btn-cancel-summary">Cancel</button>
                <button type="submit" class="btn-primary btn-save-summary">Save</button>
            </div>
            <textarea name="summary_text" class="form-control summary-textarea">${esc(summaryText)}</textarea>
        </form>`;

    const viewEl = els.projectSummary.querySelector('.summary-view');
    const formEl = els.projectSummary.querySelector('.summary-form');

    viewEl.querySelector('.btn-edit-summary').addEventListener('click', () => {
        viewEl.classList.add('hidden');
        formEl.classList.remove('hidden');
        formEl.querySelector('textarea').focus();
    });

    formEl.querySelector('.btn-cancel-summary').addEventListener('click', () => {
        formEl.classList.add('hidden');
        viewEl.classList.remove('hidden');
    });

    formEl.addEventListener('submit', async (e) => {
        e.preventDefault();
        const saveBtn = formEl.querySelector('.btn-save-summary');
        saveBtn.textContent = 'Saving…';
        saveBtn.disabled = true;
        try {
            const data = { summary_text: formEl.querySelector('textarea').value };
            await api.post(`/api/projects/${state.activeProjectId}/summary`, data);
            await selectProject(state.activeProjectId, 'summary', { updatePath: false });
        } catch (err) {
            alert('Failed to save: ' + err.message);
            saveBtn.textContent = 'Save';
            saveBtn.disabled = false;
        }
    });
}

async function deleteProject(id) {
    if (!confirm('Are you sure you want to delete this project?')) return;
    try {
        await api.delete(`/api/projects/${id}`);
        state.projects = await api.get('/api/projects');
        showProjectEmptyState();
        renderProjectNav(selectProject);
    } catch (err) { alert(err.message); }
}


async function deleteTask(id) {
    if (!confirm('Delete this task?')) return;
    try {
        await api.delete(`/api/projects/${state.activeProjectId}/tasks/${id}`);
        await refreshTasks();
    } catch (err) { alert(err.message); }
}

function showDecisionForm(dec = null) {
    const html = `
    <form data-type="decision" data-id="${dec ? dec.id : ''}">
        <div class="form-group"><label>Title</label><input name="title" class="form-control" value="${dec ? esc(dec.title) : ''}" required></div>
        <div class="form-group"><label>Decision Text</label><textarea name="decision_text" class="form-control" required>${dec ? esc(dec.decision_text) : ''}</textarea></div>
        <div class="form-group"><label>Rationale</label><textarea name="rationale" class="form-control">${dec ? esc(dec.rationale) : ''}</textarea></div>
        <div class="form-group"><label>Status</label><select name="status" class="form-control">
            <option value="active" ${dec?.status === 'active' || !dec ? 'selected' : ''}>Active</option>
            <option value="draft" ${dec?.status === 'draft' ? 'selected' : ''}>Draft</option>
            <option value="superseded" ${dec?.status === 'superseded' ? 'selected' : ''}>Superseded</option>
        </select></div>
    </form>`;
    showModal(dec ? 'Edit Decision' : 'New Decision', html);
}

async function deleteDecision(id) {
    if (!confirm('Delete this decision?')) return;
    try {
        await api.delete(`/api/projects/${state.activeProjectId}/decisions/${id}`);
        await refreshDecisions();
    } catch (err) { alert(err.message); }
}

function showNoteForm(note = null) {
    const html = `
    <form data-type="note" data-id="${note ? note.id : ''}">
        <div class="form-group"><label>Title</label><input name="title" class="form-control" value="${note ? esc(note.title) : ''}" required></div>
        <div class="form-group"><label>Note Text</label><textarea name="note_text" class="form-control" required>${note ? esc(note.note_text) : ''}</textarea></div>
        <div class="form-group"><label>Type</label><select name="note_type" class="form-control">
            <option value="context" ${note?.note_type === 'context' || !note ? 'selected' : ''}>Context</option>
            <option value="investigation" ${note?.note_type === 'investigation' ? 'selected' : ''}>Investigation</option>
            <option value="implementation" ${note?.note_type === 'implementation' ? 'selected' : ''}>Implementation</option>
            <option value="bug" ${note?.note_type === 'bug' ? 'selected' : ''}>Bug</option>
            <option value="handover" ${note?.note_type === 'handover' ? 'selected' : ''}>Handover</option>
        </select></div>
    </form>`;
    showModal(note ? 'Edit Note' : 'New Note', html);
}

async function deleteNote(id) {
    if (!confirm('Delete this note?')) return;
    try {
        await api.delete(`/api/projects/${state.activeProjectId}/notes/${id}`);
        await refreshNotes();
    } catch (err) { alert(err.message); }
}


function showGlobalNoteForm(note = null) {
    const html = `
    <form data-type="global_note" data-id="${note ? note.id : ''}">
        <div class="form-group"><label>Title</label><input name="title" class="form-control" value="${note ? esc(note.title) : ''}" required></div>
        <div class="form-group"><label>Note</label><textarea name="note_text" class="form-control" required>${note ? esc(note.note_text) : ''}</textarea></div>
        <div class="form-group"><label>Type</label><select name="note_type" class="form-control">
            <option value="context" ${note?.note_type === 'context' || !note ? 'selected' : ''}>Context</option>
            <option value="investigation" ${note?.note_type === 'investigation' ? 'selected' : ''}>Investigation</option>
            <option value="implementation" ${note?.note_type === 'implementation' ? 'selected' : ''}>Implementation</option>
            <option value="bug" ${note?.note_type === 'bug' ? 'selected' : ''}>Bug</option>
            <option value="handover" ${note?.note_type === 'handover' ? 'selected' : ''}>Handover</option>
        </select></div>
    </form>`;
    showModal(note ? 'Edit Global Note' : 'New Global Note', html);
}

async function deleteGlobalNote(id) {
    if (!confirm('Delete this global note?')) return;
    try {
        await api.delete(`/api/global-notes/${id}`);
        await loadGlobalNotes();
    } catch (err) { alert(err.message); }
}

// ── marked config — escape raw HTML to prevent parser breakage ──────────────

marked.use({
    renderer: {
        html({ text }) {
            return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }
    }
});

// ── Init ───────────────────────────────────────────────────────────────────────

async function init() {
    try {
        state.projects = await api.get('/api/projects');
    } catch { state.projects = []; }

    await loadGlobalNotes();
    renderProjectNav(selectProject);
    bindTabs();
    bindFilters();

    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            state.hiddenAt = Date.now();
        } else {
            const wasHiddenMs = state.hiddenAt ? Date.now() - state.hiddenAt : 0;
            state.hiddenAt = null;
            if (wasHiddenMs > HIDDEN_STALE_MS && state.activeProjectId) {
                refreshProjectData();
            }
        }
    });

    els.addGlobalNoteBtn.addEventListener('click', () => showGlobalNoteForm());

    // Make sure we catch clicks even if dom.js is cached by the browser
    document.addEventListener('click', (e) => {
        if (e.target.closest('#global-workspace-btn')) {
            selectGlobalWorkspace('notes');
        }
        if (!e.target.closest('.task-status-dropdown')) {
            document.querySelectorAll('.task-status-options').forEach(o => o.classList.add('hidden'));
        }

        const chip = e.target.closest('.entity-id-chip');
        if (chip) {
            e.stopPropagation();
            const fullId = chip.dataset.fullId;
            navigator.clipboard.writeText(fullId).then(() => {
                const idText = chip.querySelector('.id-text');
                const original = idText.textContent;
                idText.textContent = '✓';
                chip.classList.add('copied');
                setTimeout(() => {
                    idText.textContent = original;
                    chip.classList.remove('copied');
                }, 1500);
            });
        }
    });

    if (els.globalNoteFilters) {
        els.globalNoteFilters.addEventListener('click', e => {
            const btn = e.target.closest('.filter-btn');
            if (!btn) return;
            els.globalNoteFilters.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.globalNoteFilter = btn.dataset.type;
            renderGlobalNotes(getGlobalNoteHandlers());
        });
    }
    bindTaskListEvents();
    bindTaskDetailEvents();
    bindNoteDetailEvents();
    bindDecisionListEvents();
    bindNoteListEvents();

    bindKanbanEvents(
        // onStatusChange — PATCH status then refresh with board tab active
        async (taskId, newStatus) => {
            try {
                await api.patch(`/api/projects/${state.activeProjectId}/tasks/${taskId}`, { status: newStatus });
                await refreshTasks();
            } catch (err) {
                alert(err.message);
            }
        },
        // onCardClick — navigate to task detail page
        (taskId) => {
            const proj = state.projects.find(p => p.id === state.activeProjectId);
            if (proj) selectTaskDetail(proj.name, taskId);
        }
    );

    els.addProjectBtn.addEventListener('click', () => showProjectForm());
    els.editProjectBtn.addEventListener('click', () => {
        const proj = state.projects.find(p => p.id === state.activeProjectId);
        if (proj) showProjectForm(proj);
    });
    els.deleteProjectBtn.addEventListener('click', () => deleteProject(state.activeProjectId));

    els.addTaskBtn.addEventListener('click', () => showAddTopTaskForm());
    els.addDecisionBtn.addEventListener('click', () => showDecisionForm());
    els.addNoteBtn.addEventListener('click', () => showNoteForm());

    els.modalClose.addEventListener('click', hideModal);
    els.modalCancel.addEventListener('click', hideModal);
    els.modalSave.addEventListener('click', () => {
        const tab = getActiveTab();
        els.modalSave.disabled = true;
        handleModalSave({
            onProjectUpdate: async () => { state.projects = await api.get('/api/projects'); renderProjectNav(selectProject); },
            onTaskUpdate: () => refreshTasks(),
            onDecisionUpdate: () => refreshDecisions(),
            onNoteUpdate: () => refreshNotes(),
            onTaskNoteUpdate: (taskId) => loadTaskNotes(taskId),
            onGlobalNoteUpdate: () => loadGlobalNotes()
        }).finally(() => { els.modalSave.disabled = false; });
    });
    els.modalOverlay.addEventListener('click', e => { if (e.target === els.modalOverlay) hideModal(); });

    // Search mode toggle
    document.querySelectorAll('.toggle-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const mode = btn.dataset.mode;
            state.searchMode = mode;

            // Update active state
            document.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Update search input placeholder
            const placeholder = mode === 'current' ? 'Search current project...' : 'Search all projects...';
            els.searchInput.placeholder = placeholder;
        });
    });

    els.searchInput.addEventListener('keyup', e => {
        if (e.key === 'Enter') {
            const query = els.searchInput.value.trim();
            if (query) performSearch(query);
        }
    });

    els.clearSearchBtn.addEventListener('click', () => {
        els.searchInput.value = '';
        state.searchResults = null;
        els.searchTab.classList.add('hidden');
        activateTab('summary');
    });

    els.searchResultsList.addEventListener('click', async e => {
        const item = e.target.closest('.search-result-item--clickable');
        if (!item) return;

        const entityType = item.dataset.entityType;
        const entityId = item.dataset.entityId;
        const projectName = item.dataset.projectName;
        const taskId = item.dataset.taskId;

        const { entityNavTarget } = await import('./utils.js');
        const target = entityNavTarget({ entity_type: entityType, id: entityId, project_name: projectName, task_id: taskId });
        if (!target) return;

        const scrollAndHighlight = () => {
            const el = document.getElementById(target.anchor);
            if (!el) return;
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            el.classList.add('highlight-flash');
            setTimeout(() => el.classList.remove('highlight-flash'), 1500);
        };

        // Navigate to detail pages for task and note results
        if (entityType === 'task') {
            await selectTaskDetail(projectName, entityId);
            return;
        }
        if (entityType === 'task_note') {
            await selectTaskDetail(projectName, taskId || entityId);
            return;
        }
        if (entityType === 'note') {
            await selectNoteDetail(projectName, entityId);
            return;
        }
        if (entityType === 'global_note') {
            await selectNoteDetail(null, entityId, { isGlobal: true });
            return;
        }

        if (target.projectName === null) {
            await selectGlobalWorkspace(target.tab, { updatePath: true });
            setTimeout(scrollAndHighlight, 100);
        } else {
            const proj = state.projects.find(p => p.name === target.projectName);
            if (!proj) return;
            await selectProject(proj.id, target.tab);
            setTimeout(scrollAndHighlight, 100);
        }
    });

    const route = parsePath();
    if (route) {
        if (route.namespace === 'global') {
            await selectGlobalWorkspace(route.tab, { updatePath: false });
        } else if (route.namespace === 'task') {
            await selectTaskDetail(route.projectName, route.taskId, { updatePath: false });
        } else if (route.namespace === 'note') {
            await selectNoteDetail(route.projectName, route.noteId, { updatePath: false });
        } else if (route.namespace === 'global_note') {
            await selectNoteDetail(null, route.noteId, { isGlobal: true, updatePath: false });
        } else {
            const proj = state.projects.find(p => p.name === route.projectName);
            if (proj) {
                history.replaceState({ namespace: 'project', projectName: proj.name, tab: route.tab }, '', location.pathname);
                await selectProject(proj.id, route.tab, { updatePath: false });
            }
        }
    }

    window.addEventListener('popstate', async e => {
        const s = e.state;
        if (s) {
            if (s.namespace === 'global') {
                await selectGlobalWorkspace(s.tab || 'notes', { updatePath: false });
            } else if (s.namespace === 'task') {
                await selectTaskDetail(s.projectName, s.taskId, { updatePath: false });
            } else if (s.namespace === 'note') {
                await selectNoteDetail(s.projectName, s.noteId, { updatePath: false });
            } else if (s.namespace === 'global_note') {
                await selectNoteDetail(null, s.noteId, { isGlobal: true, updatePath: false });
            } else if (s.projectName) {
                const proj = state.projects.find(p => p.name === s.projectName);
                if (proj) await selectProject(proj.id, s.tab || 'summary', { updatePath: false });
            }
        } else {
            showProjectEmptyState();
        }
    });
}

init();
