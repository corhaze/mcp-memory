/* app.js — Main entry point (initialization and coordination) */

import { els, $ } from './dom.js';
import { state } from './state.js';
import { api } from './api.js';
import { parsePath, setPath, setGlobalPath, VALID_TABS } from './router.js';
import { showModal, hideModal, handleModalSave } from './components/modal.js';
import { renderProjectNav, updateNavHighlight, showProjectEmptyState, renderProjectHeader } from './components/projects.js';
import { renderTasks, findTask } from './components/tasks.js';
import { renderDecisions } from './components/decisions.js';
import { renderNotes } from './components/notes.js';
import { renderGlobalNotes } from './components/global-notes.js';
import { renderTimeline } from './components/timeline.js';
import { renderSearch } from './components/search.js';
import { renderKanban, bindKanbanEvents } from './components/kanban.js';

import { esc } from './utils.js';

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

    els.emptyState.classList.add('hidden');
    els.projectView.classList.add('hidden');
    if (els.globalView) els.globalView.classList.remove('hidden');
    els.searchInput.disabled = true;

    activateTab('global-notes');

    // Fetch and render to ensure we have latest data
    await loadGlobalNotes();

    if (updatePath) {
        setGlobalPath(tab);
    }
}

async function loadTaskNotes(taskId) {
    // This will trigger the component to load and render itself
    // For now we delegate back to the component logic if we move it there
    // but to avoid circular deps we handle the refresh logic here.
    try {
        const notes = await api.get(`/api/tasks/${taskId}/notes`);
        state.taskNotes[taskId] = notes;
        const container = document.getElementById(`task-notes-${taskId}`);
        if (container) {
            import('./components/tasks.js').then(m => {
                container.innerHTML = m.renderTaskNotesHtml(taskId, notes);
                bindTaskNoteButtons(taskId);
            });
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

// ── Project Selection ─────────────────────────────────────────────────────────

async function selectProject(id, tab = 'summary', { updatePath = true } = {}) {
    state.activeProjectId = id;
    state.activeView = 'project';
    state.expandedTasks.clear();

    updateNavHighlight(id);
    els.globalWorkspaceBtn?.classList.remove('active');

    els.emptyState.classList.add('hidden');
    els.projectView.classList.remove('hidden');
    if (els.globalView) els.globalView.classList.add('hidden');
    els.searchInput.disabled = false;

    try {
        const [ctx, tasks, decisions, notes, timeline] = await Promise.all([
            api.get(`/api/projects/${id}`),
            api.get(`/api/projects/${id}/tasks?topo=true`),
            api.get(`/api/projects/${id}/decisions`),
            api.get(`/api/projects/${id}/notes`),
            api.get(`/api/projects/${id}/timeline`),
        ]);

        state.tasks = tasks || [];
        state.decisions = decisions || [];
        state.notes = notes || [];
        state.timeline = timeline || [];

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

    bindTaskEvents();
    bindDecisionEvents();
    bindNoteEvents();

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
        bindTaskEvents();
    });

    els.decisionFilters.addEventListener('click', e => {
        const btn = e.target.closest('.filter-btn');
        if (!btn) return;
        els.decisionFilters.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.decisionFilter = btn.dataset.status;
        renderDecisions();
        bindDecisionEvents();
    });

    els.noteFilters.addEventListener('click', e => {
        const btn = e.target.closest('.filter-btn');
        if (!btn) return;
        els.noteFilters.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.noteFilter = btn.dataset.type;
        renderNotes();
        bindNoteEvents();
    });
}

// ── Search ─────────────────────────────────────────────────────────────────────

async function performSearch(query) {
    if (state.searchMode === 'current' && !state.activeProjectId) return;
    try {
        // Build search endpoint with mode-based parameters
        let searchUrl = `/api/search?q=${encodeURIComponent(query)}&limit=10`;
        if (state.searchMode === 'current' && state.activeProjectId) {
            searchUrl += `&project_id=${encodeURIComponent(state.activeProjectId)}`;
        }

        const results = await api.get(searchUrl);
        state.searchResults = results;
        els.searchTab.classList.remove('hidden');
        activateTab('search');
        renderSearch({
            onTasksRender: (container) => {
                container.querySelectorAll('.task-toggle').forEach(btn => {
                    btn.addEventListener('click', (e) => handleTaskToggle(e, btn));
                });
                container.querySelectorAll('.add-task-note-btn').forEach(btn => {
                    btn.addEventListener('click', (e) => { e.stopPropagation(); showTaskNoteForm(btn.dataset.taskId); });
                });
                container.querySelectorAll('.edit-task').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        // Search in both project tasks and search result tasks to find the item
                        const task = findTask(btn.dataset.id, state.tasks) || findTask(btn.dataset.id, state.searchResults.tasks);
                        if (task) showTaskForm(task);
                    });
                });
                container.querySelectorAll('.delete-task').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        deleteTask(btn.dataset.id);
                    });
                });
            },
            onDecisionsRender: (container) => {
                container.querySelectorAll('.edit-decision').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        const dec = state.searchResults.decisions.find(d => d.id === btn.dataset.id);
                        if (dec) showDecisionForm(dec);
                    });
                });
                container.querySelectorAll('.delete-decision').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        deleteDecision(btn.dataset.id);
                    });
                });
            },
            onNotesRender: (container) => {
                container.querySelectorAll('.edit-note').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        const note = state.searchResults.notes.find(n => n.id === btn.dataset.id);
                        if (note) showNoteForm(note);
                    });
                });
                container.querySelectorAll('.delete-note').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        deleteNote(btn.dataset.id);
                    });
                });
            }
        });
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

        // Refresh the project view to show the new subtask
        await selectProject(state.activeProjectId, getActiveTab());
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

function bindTaskEvents() {
    els.taskListEl.querySelectorAll('.task-status-trigger').forEach(btn => {
        btn.addEventListener('click', e => {
            e.stopPropagation();
            const dropdown = btn.closest('.task-status-dropdown');
            const options = dropdown.querySelector('.task-status-options');
            const isOpen = !options.classList.contains('hidden');
            document.querySelectorAll('.task-status-options').forEach(o => o.classList.add('hidden'));
            if (!isOpen) options.classList.remove('hidden');
        });
    });

    els.taskListEl.querySelectorAll('.task-status-options .status-option').forEach(opt => {
        opt.addEventListener('click', async e => {
            e.stopPropagation();
            const dropdown = opt.closest('.task-status-dropdown');
            const taskId = dropdown.dataset.taskId;
            const newStatus = opt.dataset.value;
            dropdown.querySelector('.task-status-options').classList.add('hidden');
            try {
                await api.patch(`/api/projects/${state.activeProjectId}/tasks/${taskId}`, { status: newStatus });
                await selectProject(state.activeProjectId, getActiveTab());
            } catch (err) {
                alert(err.message);
            }
        });
    });

    els.taskListEl.querySelectorAll('.task-toggle').forEach(btn => {
        btn.addEventListener('click', e => handleTaskToggle(e, btn));
    });

    els.taskListEl.querySelectorAll('.add-task-note-btn').forEach(btn => {
        btn.addEventListener('click', e => {
            e.stopPropagation();
            showTaskNoteForm(btn.dataset.taskId);
        });
    });

    els.taskListEl.querySelectorAll('.edit-task').forEach(btn => {
        btn.addEventListener('click', e => {
            e.stopPropagation();
            const task = findTask(btn.dataset.id, state.tasks);
            if (task) showTaskForm(task);
        });
    });

    els.taskListEl.querySelectorAll('.delete-task').forEach(btn => {
        btn.addEventListener('click', e => {
            e.stopPropagation();
            deleteTask(btn.dataset.id);
        });
    });

    // Add subtask form toggle handler
    els.taskListEl.querySelectorAll('.add-subtask-btn').forEach(btn => {
        btn.addEventListener('click', e => {
            e.stopPropagation();
            toggleAddSubtaskForm(btn);
        });
    });

    // Add subtask form submit handler
    els.taskListEl.querySelectorAll('.add-subtask-form').forEach(form => {
        const submitBtn = form.querySelector('.btn-submit');
        if (submitBtn) {
            submitBtn.addEventListener('click', async e => {
                e.preventDefault();
                e.stopPropagation();
                await submitAddSubtaskForm(form);
            });
        }
    });

    // Cancel subtask form handler
    els.taskListEl.querySelectorAll('.btn-cancel').forEach(btn => {
        btn.addEventListener('click', e => {
            e.preventDefault();
            e.stopPropagation();
            cancelAddSubtaskForm(btn);
        });
    });
}

function bindDecisionEvents() {
    els.decisionListEl.querySelectorAll('.edit-decision').forEach(btn => {
        btn.addEventListener('click', () => {
            const dec = state.decisions.find(d => d.id === btn.dataset.id);
            if (dec) showDecisionForm(dec);
        });
    });
    els.decisionListEl.querySelectorAll('.delete-decision').forEach(btn => {
        btn.addEventListener('click', () => deleteDecision(btn.dataset.id));
    });
}

function bindNoteEvents() {
    els.noteListEl.querySelectorAll('.edit-note').forEach(btn => {
        btn.addEventListener('click', () => {
            const note = state.notes.find(n => n.id === btn.dataset.id);
            if (note) showNoteForm(note);
        });
    });
    els.noteListEl.querySelectorAll('.delete-note').forEach(btn => {
        btn.addEventListener('click', () => deleteNote(btn.dataset.id));
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

function showTaskForm(task = null) {
    const html = `
    <form data-type="task" data-id="${task ? task.id : ''}">
        <div class="form-group"><label>Title</label><input name="title" class="form-control" value="${task ? esc(task.title) : ''}" required></div>
        <div class="form-group"><label>Description</label><textarea name="description" class="form-control">${task ? esc(task.description) : ''}</textarea></div>
        <div class="form-group"><label>Status</label><select name="status" class="form-control">
            <option value="open" ${task?.status === 'open' ? 'selected' : ''}>Open</option>
            <option value="in_progress" ${task?.status === 'in_progress' ? 'selected' : ''}>In Progress</option>
            <option value="blocked" ${task?.status === 'blocked' ? 'selected' : ''}>Blocked</option>
            <option value="done" ${task?.status === 'done' ? 'selected' : ''}>Done</option>
            <option value="cancelled" ${task?.status === 'cancelled' ? 'selected' : ''}>Cancelled</option>
        </select></div>
        <div class="form-group"><label>Urgent</label><input type="checkbox" name="urgent" ${task?.urgent ? 'checked' : ''} /></div>
        <div class="form-group"><label>Complex</label><input type="checkbox" name="complex" ${task?.complex ? 'checked' : ''} /></div>
        <div class="form-group"><label>Assigned Agent</label><input name="assigned_agent" class="form-control" value="${task ? esc(task.assigned_agent) : ''}"></div>
        <div class="form-group"><label>Parent Task ID</label><input name="parent_task_id" class="form-control" value="${task ? esc(task.parent_task_id) : ''}"></div>
        <div class="form-group"><label>Blocked By Task ID</label><input name="blocked_by_task_id" class="form-control" value="${task ? esc(task.blocked_by_task_id) : ''}"></div>
        <div class="form-group"><label>Next Action</label><input name="next_action" class="form-control" value="${task ? esc(task.next_action) : ''}"></div>
    </form>`;
    showModal(task ? 'Edit Task' : 'New Task', html);
}

async function deleteTask(id) {
    if (!confirm('Delete this task?')) return;
    try {
        await api.delete(`/api/projects/${state.activeProjectId}/tasks/${id}`);
        await selectProject(state.activeProjectId);
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
        await selectProject(state.activeProjectId);
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
        await selectProject(state.activeProjectId);
    } catch (err) { alert(err.message); }
}

function showTaskNoteForm(taskId) {
    const html = `
    <form data-type="task_note" data-task-id="${taskId}">
        <div class="form-group"><label>Title</label><input name="title" class="form-control" required></div>
        <div class="form-group"><label>Note</label><textarea name="note_text" class="form-control" required></textarea></div>
        <div class="form-group"><label>Type</label><select name="note_type" class="form-control">
            <option value="context">Context</option>
            <option value="investigation">Investigation</option>
            <option value="implementation">Implementation</option>
            <option value="bug">Bug</option>
            <option value="handover">Handover</option>
        </select></div>
    </form>`;
    showModal('Add Task Note', html);
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

    els.addGlobalNoteBtn.addEventListener('click', () => showGlobalNoteForm());

    // Make sure we catch clicks even if dom.js is cached by the browser
    document.addEventListener('click', (e) => {
        if (e.target.closest('#global-workspace-btn')) {
            selectGlobalWorkspace('notes');
        }
        if (!e.target.closest('.task-status-dropdown')) {
            document.querySelectorAll('.task-status-options').forEach(o => o.classList.add('hidden'));
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
    bindKanbanEvents(
        // onStatusChange — PATCH status then refresh with board tab active
        async (taskId, newStatus) => {
            try {
                await api.patch(`/api/projects/${state.activeProjectId}/tasks/${taskId}`, { status: newStatus });
                await selectProject(state.activeProjectId, 'board');
            } catch (err) {
                alert(err.message);
            }
        },
        // onCardClick — switch to Tasks tab with the task expanded
        (taskId) => {
            state.expandedTasks.add(taskId);
            // Reset filter so the task is visible regardless of its status.
            state.taskFilter = '';
            els.taskFilters.querySelectorAll('.filter-btn').forEach(b => {
                b.classList.toggle('active', b.dataset.status === '');
            });
            renderTasks();
            bindTaskEvents();
            activateTab('tasks');
            const proj = state.projects.find(p => p.id === state.activeProjectId);
            if (proj) setPath(proj.name, 'tasks', true);
            // Scroll to task and load notes after the tab paint settles.
            requestAnimationFrame(() => {
                const taskEl = document.querySelector(`.task-group [data-task-id="${taskId}"]`)
                    ?.closest('.task-group');
                if (taskEl) taskEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                if (!state.taskNotes[taskId]) loadTaskNotes(taskId);
            });
        }
    );

    els.addProjectBtn.addEventListener('click', () => showProjectForm());
    els.editProjectBtn.addEventListener('click', () => {
        const proj = state.projects.find(p => p.id === state.activeProjectId);
        if (proj) showProjectForm(proj);
    });
    els.deleteProjectBtn.addEventListener('click', () => deleteProject(state.activeProjectId));

    els.addTaskBtn.addEventListener('click', () => showTaskForm());
    els.addDecisionBtn.addEventListener('click', () => showDecisionForm());
    els.addNoteBtn.addEventListener('click', () => showNoteForm());

    els.modalClose.addEventListener('click', hideModal);
    els.modalCancel.addEventListener('click', hideModal);
    els.modalSave.addEventListener('click', () => {
        const tab = getActiveTab();
        els.modalSave.disabled = true;
        handleModalSave({
            onProjectUpdate: async () => { state.projects = await api.get('/api/projects'); renderProjectNav(selectProject); },
            onTaskUpdate: () => selectProject(state.activeProjectId, tab),
            onDecisionUpdate: () => selectProject(state.activeProjectId, tab),
            onNoteUpdate: () => selectProject(state.activeProjectId, tab),
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

    const route = parsePath();
    if (route) {
        if (route.namespace === 'global') {
            await selectGlobalWorkspace(route.tab, { updatePath: false });
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
