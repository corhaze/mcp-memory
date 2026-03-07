/* index.js — mcp-memory Explorer UI application logic */

'use strict';

// ── State ──────────────────────────────────────────────────────────────────────
const state = {
    projects: [],
    activeProjectId: null,
    tasks: [],
    decisions: [],
    notes: [],
    timeline: [],
    taskFilter: 'open',
    decisionFilter: '',
    noteFilter: '',
    expandedTasks: new Set(),
    searchResults: null,
};

// ── API ────────────────────────────────────────────────────────────────────────
const api = {
    async request(path, method = 'GET', body = null) {
        const options = { method };
        if (body) {
            options.headers = { 'Content-Type': 'application/json' };
            options.body = JSON.stringify(body);
        }
        const res = await fetch(path, options);
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || `API error: ${res.status}`);
        }
        return res.json();
    },
    get(path) { return this.request(path, 'GET'); },
    post(path, body) { return this.request(path, 'POST', body); },
    patch(path, body) { return this.request(path, 'PATCH', body); },
    delete(path) { return this.request(path, 'DELETE'); }
};

// ── DOM refs ───────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const projectList = $('project-list');
const emptyState = $('empty-state');
const projectView = $('project-view');
const projectName = $('project-name');
const projectStatus = $('project-status-badge');
const projectDesc = $('project-description');
const projectSummary = $('project-summary-text');
const taskListEl = $('task-list');
const decisionListEl = $('decision-list');
const noteListEl = $('note-list');
const timelineListEl = $('timeline-list');

const searchInput = $('global-search-input');
const searchTab = $('tab-search');
const clearSearchBtn = $('clear-search-btn');
const searchTasksList = $('search-tasks-list');
const searchDecisionsList = $('search-decisions-list');
const searchNotesList = $('search-notes-list');
const searchEmptyState = $('search-empty-state');

// ── Routing ────────────────────────────────────────────────────────────────────
// URL format: /{project-name}/{tab}  e.g. /mcp-memory/decisions
const VALID_TABS = ['summary', 'tasks', 'decisions', 'notes', 'timeline', 'search'];

function parsePath() {
    const parts = location.pathname.replace(/^\//, '').split('/').filter(Boolean);
    if (!parts.length) return null;
    const projectName = decodeURIComponent(parts[0]);
    const tab = VALID_TABS.includes(parts[1]) ? parts[1] : 'summary';
    return { projectName, tab };
}

function setPath(projectName, tab, replace = false) {
    const url = `/${encodeURIComponent(projectName)}/${tab}`;
    if (replace) {
        history.replaceState({ projectName, tab }, '', url);
    } else {
        history.pushState({ projectName, tab }, '', url);
    }
}

// ── Init ───────────────────────────────────────────────────────────────────────
async function init() {
    try {
        state.projects = await api.get('/api/projects');
    } catch {
        state.projects = [];
    }
    renderProjectNav();
    bindTabs();
    bindFilters();

    // Search events
    searchInput.addEventListener('keyup', e => {
        if (e.key === 'Enter') {
            const query = searchInput.value.trim();
            if (query) performSearch(query);
        }
    });

    clearSearchBtn.addEventListener('click', () => {
        searchInput.value = '';
        state.searchResults = null;
        searchTab.classList.add('hidden');
        activateTab('summary');
    });

    // Event Listeners for CRUD
    $('add-project-btn').addEventListener('click', () => showProjectForm());
    $('edit-project-btn').addEventListener('click', () => {
        const proj = state.projects.find(p => p.id === state.activeProjectId);
        if (proj) showProjectForm(proj);
    });
    $('delete-project-btn').addEventListener('click', () => deleteProject(state.activeProjectId));

    $('add-task-btn').addEventListener('click', () => showTaskForm());
    $('add-decision-btn').addEventListener('click', () => showDecisionForm());
    $('add-note-btn').addEventListener('click', () => showNoteForm());

    $('modal-close').addEventListener('click', hideModal);
    $('modal-cancel').addEventListener('click', hideModal);
    $('modal-save').addEventListener('click', handleModalSave);
    $('modal-overlay').addEventListener('click', e => { if (e.target === $('modal-overlay')) hideModal(); });

    // Restore state from URL on load
    const route = parsePath();
    if (route) {
        const proj = state.projects.find(p => p.name === route.projectName);
        if (proj) {
            // replaceState so init doesn't add a spurious history entry
            history.replaceState({ projectName: proj.name, tab: route.tab }, '', location.pathname);
            await selectProject(proj.id, route.tab, { updatePath: false });
        }
    }

    // Handle back/forward
    window.addEventListener('popstate', async e => {
        const s = e.state;
        if (s && s.projectName) {
            const proj = state.projects.find(p => p.name === s.projectName);
            if (proj) {
                await selectProject(proj.id, s.tab || 'summary', { updatePath: false });
            }
        } else {
            // Navigated back to no-project state
            state.activeProjectId = null;
            emptyState.classList.remove('hidden');
            projectView.classList.add('hidden');
            document.querySelectorAll('.project-nav-item').forEach(b => b.classList.remove('active'));
        }
    });
}

// ── Project nav ────────────────────────────────────────────────────────────────
function renderProjectNav() {
    if (!state.projects.length) {
        projectList.innerHTML = '<p class="nav-hint">No projects found.</p>';
        return;
    }
    projectList.innerHTML = state.projects.map(p => `
    <button class="project-nav-item${state.activeProjectId === p.id ? ' active' : ''}"
            data-id="${p.id}"
            id="proj-nav-${p.id}">
      <span class="proj-dot"></span>
      <span>${esc(p.name)}</span>
    </button>
  `).join('');

    projectList.querySelectorAll('.project-nav-item').forEach(btn => {
        btn.addEventListener('click', () => selectProject(btn.dataset.id));
    });
}

async function selectProject(id, tab = 'summary', { updatePath = true } = {}) {
    state.activeProjectId = id;
    state.expandedTasks.clear();

    // Update nav highlight
    document.querySelectorAll('.project-nav-item').forEach(b => {
        b.classList.toggle('active', b.dataset.id === id);
    });

    // Show project view, hide empty state
    emptyState.classList.add('hidden');
    projectView.classList.remove('hidden');
    searchInput.disabled = false;

    // Load all data in parallel
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
}

function renderProjectView(ctx, tab = 'summary', updatePath = true) {
    const id = state.activeProjectId;
    const proj = ctx.project || {};
    projectName.textContent = proj.name || id;
    projectDesc.textContent = proj.description || '';
    projectStatus.textContent = proj.status || '';
    projectStatus.className = `status-badge badge-${proj.status || 'active'}`;
    if (ctx.summary) {
        projectSummary.innerHTML = marked.parse(ctx.summary);
    } else {
        projectSummary.innerHTML = '<p class="nav-hint">No project summary available. Be sure to call add_project_summary.</p>';
    }

    // Render panels
    renderTasks();
    renderDecisions();
    renderNotes();
    renderTimeline();

    // Activate the correct tab
    activateTab(tab);

    // Update URL (push new entry unless we're restoring from popstate)
    if (updatePath) {
        const proj = state.projects.find(p => p.id === id);
        if (proj) setPath(proj.name, tab);
    }
}

// ── Modals & CRUD ─────────────────────────────────────────────────────────────
function showModal(title, contentHtml) {
    $('modal-title').textContent = title;
    $('modal-body').innerHTML = contentHtml;
    initCustomSelects($('modal-body'));
    $('modal-overlay').classList.remove('hidden');
}

function hideModal() {
    $('modal-overlay').classList.add('hidden');
    $('modal-body').innerHTML = '';
}

function initCustomSelects(container) {
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

document.addEventListener('click', () => {
    document.querySelectorAll('.custom-select-options').forEach(el => el.classList.add('hidden'));
});

async function handleModalSave() {
    const form = $('modal-body').querySelector('form');
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

    // Handle checkbox for urgent field (FormData won't include it if unchecked)
    if (type === 'task') {
        data['urgent'] = !!data['urgent'];
    }

    try {
        if (type === 'project') {
            if (id) await api.patch(`/api/projects/${id}`, data);
            else await api.post('/api/projects', data);
            state.projects = await api.get('/api/projects');
            renderProjectNav();
            if (id === state.activeProjectId) await selectProject(id);
        } else if (type === 'task') {
            if (id) await api.patch(`/api/projects/${state.activeProjectId}/tasks/${id}`, data);
            else await api.post(`/api/projects/${state.activeProjectId}/tasks`, data);
            await selectProject(state.activeProjectId);
        } else if (type === 'decision') {
            if (id) await api.patch(`/api/projects/${state.activeProjectId}/decisions/${id}`, data);
            else await api.post(`/api/projects/${state.activeProjectId}/decisions`, data);
            await selectProject(state.activeProjectId);
        } else if (type === 'note') {
            if (id) await api.patch(`/api/projects/${state.activeProjectId}/notes/${id}`, data);
            else await api.post(`/api/projects/${state.activeProjectId}/notes`, data);
            await selectProject(state.activeProjectId);
        }
        hideModal();
    } catch (err) {
        alert(err.message);
    }
}

function showProjectForm(proj = null) {
    const html = `
    <form data-type="project" data-id="${proj ? proj.id : ''}">
        <div class="form-group">
            <label>Name</label>
            <input name="name" class="form-control" value="${proj ? esc(proj.name) : ''}" required ${proj ? 'readonly' : ''}>
        </div>
        <div class="form-group">
            <label>Description</label>
            <textarea name="description" class="form-control">${proj ? esc(proj.description) : ''}</textarea>
        </div>
        <div class="form-group">
            <label>Status</label>
            <select name="status" class="form-control">
                <option value="active" ${proj?.status === 'active' ? 'selected' : ''}>Active</option>
                <option value="archived" ${proj?.status === 'archived' ? 'selected' : ''}>Archived</option>
            </select>
        </div>
    </form>`;
    showModal(proj ? 'Edit Project' : 'New Project', html);
}

async function deleteProject(id) {
    if (!confirm('Are you sure you want to delete this project and all its data?')) return;
    try {
        await api.delete(`/api/projects/${id}`);
        state.projects = await api.get('/api/projects');
        state.activeProjectId = null;
        renderProjectNav();
        emptyState.classList.remove('hidden');
        projectView.classList.add('hidden');
    } catch (err) {
        alert(err.message);
    }
}

function showTaskForm(task = null) {
    const html = `
    <form data-type="task" data-id="${task ? task.id : ''}">
        <div class="form-group">
            <label>Title</label>
            <input name="title" class="form-control" value="${task ? esc(task.title) : ''}" required>
        </div>
        <div class="form-group">
            <label>Description</label>
            <textarea name="description" class="form-control">${task ? esc(task.description) : ''}</textarea>
        </div>
        <div class="form-group">
            <label>Status</label>
            <select name="status" class="form-control">
                <option value="open" ${task?.status === 'open' ? 'selected' : ''}>Open</option>
                <option value="in_progress" ${task?.status === 'in_progress' ? 'selected' : ''}>In Progress</option>
                <option value="blocked" ${task?.status === 'blocked' ? 'selected' : ''}>Blocked</option>
                <option value="done" ${task?.status === 'done' ? 'selected' : ''}>Done</option>
                <option value="cancelled" ${task?.status === 'cancelled' ? 'selected' : ''}>Cancelled</option>
            </select>
        </div>
        <div class="form-group">
            <label>Urgent</label>
            <input type="checkbox" name="urgent" ${task?.urgent ? 'checked' : ''} />
        </div>
        <div class="form-group">
            <label>Assigned Agent</label>
            <input name="assigned_agent" class="form-control" value="${task ? esc(task.assigned_agent) : ''}">
        </div>
        <div class="form-group">
            <label>Parent Task ID</label>
            <input name="parent_task_id" class="form-control" value="${task ? esc(task.parent_task_id) : ''}">
        </div>
        <div class="form-group">
            <label>Blocked By Task ID</label>
            <input name="blocked_by_task_id" class="form-control" value="${task ? esc(task.blocked_by_task_id) : ''}">
        </div>
        <div class="form-group">
            <label>Next Action</label>
            <input name="next_action" class="form-control" value="${task ? esc(task.next_action) : ''}">
        </div>
    </form>`;
    showModal(task ? 'Edit Task' : 'New Task', html);
}

async function deleteTask(id) {
    if (!confirm('Delete this task?')) return;
    try {
        await api.delete(`/api/projects/${state.activeProjectId}/tasks/${id}`);
        await selectProject(state.activeProjectId);
    } catch (err) {
        alert(err.message);
    }
}

function showDecisionForm(dec = null) {
    const html = `
    <form data-type="decision" data-id="${dec ? dec.id : ''}">
        <div class="form-group">
            <label>Title</label>
            <input name="title" class="form-control" value="${dec ? esc(dec.title) : ''}" required>
        </div>
        <div class="form-group">
            <label>Decision Text</label>
            <textarea name="decision_text" class="form-control" required>${dec ? esc(dec.decision_text) : ''}</textarea>
        </div>
        <div class="form-group">
            <label>Rationale</label>
            <textarea name="rationale" class="form-control">${dec ? esc(dec.rationale) : ''}</textarea>
        </div>
        <div class="form-group">
            <label>Status</label>
            <select name="status" class="form-control">
                <option value="active" ${dec?.status === 'active' || !dec ? 'selected' : ''}>Active</option>
                <option value="draft" ${dec?.status === 'draft' ? 'selected' : ''}>Draft</option>
                <option value="superseded" ${dec?.status === 'superseded' ? 'selected' : ''}>Superseded</option>
            </select>
        </div>
    </form>`;
    showModal(dec ? 'Edit Decision' : 'New Decision', html);
}

function showNoteForm(note = null) {
    const html = `
    <form data-type="note" data-id="${note ? note.id : ''}">
        <div class="form-group">
            <label>Title</label>
            <input name="title" class="form-control" value="${note ? esc(note.title) : ''}" required>
        </div>
        <div class="form-group">
            <label>Note Text</label>
            <textarea name="note_text" class="form-control" required>${note ? esc(note.note_text) : ''}</textarea>
        </div>
        <div class="form-group">
            <label>Type</label>
            <select name="note_type" class="form-control">
                <option value="context" ${note?.note_type === 'context' || !note ? 'selected' : ''}>Context</option>
                <option value="investigation" ${note?.note_type === 'investigation' ? 'selected' : ''}>Investigation</option>
                <option value="implementation" ${note?.note_type === 'implementation' ? 'selected' : ''}>Implementation</option>
                <option value="bug" ${note?.note_type === 'bug' ? 'selected' : ''}>Bug</option>
                <option value="handover" ${note?.note_type === 'handover' ? 'selected' : ''}>Handover</option>
            </select>
        </div>
    </form>`;
    showModal(note ? 'Edit Note' : 'New Note', html);
}

async function deleteNote(id) {
    if (!confirm('Delete this note?')) return;
    try {
        await api.delete(`/api/projects/${state.activeProjectId}/notes/${id}`);
        await selectProject(state.activeProjectId);
    } catch (err) {
        alert(err.message);
    }
}

// ── Tabs ───────────────────────────────────────────────────────────────────────
function activateTab(name) {
    document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
    document.querySelectorAll('.panel').forEach(p => p.classList.toggle('hidden', p.id !== `panel-${name}`));
}

function bindTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const name = tab.dataset.tab;
            activateTab(name);
            // replaceState so tab switches don't pollute history
            if (state.activeProjectId) {
                const proj = state.projects.find(p => p.id === state.activeProjectId);
                if (proj) setPath(proj.name, name, true);
            }
        });
    });
}

// ── Search ─────────────────────────────────────────────────────────────────────
async function performSearch(query) {
    if (!state.activeProjectId) return;
    try {
        const results = await api.get(`/api/projects/${state.activeProjectId}/semantic_search?q=${encodeURIComponent(query)}&limit=10`);
        state.searchResults = results;
        searchTab.classList.remove('hidden');
        activateTab('search');
        renderSearch();
    } catch (err) {
        alert(err.message);
    }
}

function renderSearch() {
    const rs = state.searchResults;
    if (!rs) return;

    const hasTasks = rs.tasks && rs.tasks.length > 0;
    const hasDecisions = rs.decisions && rs.decisions.length > 0;
    const hasNotes = rs.notes && rs.notes.length > 0;

    $('search-tasks-section').classList.toggle('hidden', !hasTasks);
    $('search-decisions-section').classList.toggle('hidden', !hasDecisions);
    $('search-notes-section').classList.toggle('hidden', !hasNotes);

    if (!hasTasks && !hasDecisions && !hasNotes) {
        searchEmptyState.classList.remove('hidden');
    } else {
        searchEmptyState.classList.add('hidden');
    }

    if (hasTasks) {
        searchTasksList.innerHTML = rs.tasks.map(t => renderTaskItem(t, 0)).join('');
        // Bind expand toggles for search results
        searchTasksList.querySelectorAll('.task-toggle').forEach(btn => {
            btn.addEventListener('click', e => {
                e.stopPropagation();
                const id = btn.dataset.taskId;
                const body = document.getElementById(`task-body-${id}`);
                const isExpanded = btn.classList.contains('open');
                if (body) body.classList.toggle('hidden', isExpanded);
                btn.classList.toggle('open', !isExpanded);
            });
        });
        searchTasksList.querySelectorAll('.edit-task').forEach(btn => {
            btn.addEventListener('click', e => {
                e.stopPropagation();
                const id = btn.dataset.id;
                const task = rs.tasks.find(t => t.id === id);
                if (task) showTaskForm(task);
            });
        });
        searchTasksList.querySelectorAll('.delete-task').forEach(btn => {
            btn.addEventListener('click', e => {
                e.stopPropagation();
                deleteTask(btn.dataset.id);
            });
        });
    }

    if (hasDecisions) {
        searchDecisionsList.innerHTML = rs.decisions.map(d => `
        <li class="decision-item ${d.status === 'superseded' ? 'superseded' : ''}">
          <div class="decision-header">
            <span class="decision-title">${esc(d.title)}</span>
            <div class="header-actions">
              <button class="icon-btn edit-decision" data-id="${d.id}">✎</button>
              <button class="icon-btn danger delete-decision" data-id="${d.id}">🗑</button>
            </div>
            <span class="status-badge badge-${d.status}">${d.status}</span>
          </div>
          <div class="decision-text">${esc(d.decision_text)}</div>
          ${d.rationale ? `<div class="decision-rationale">${esc(d.rationale)}</div>` : ''}
        </li>
      `).join('');

        searchDecisionsList.querySelectorAll('.edit-decision').forEach(btn => {
            btn.addEventListener('click', () => {
                const dec = rs.decisions.find(d => d.id === btn.dataset.id);
                if (dec) showDecisionForm(dec);
            });
        });
        searchDecisionsList.querySelectorAll('.delete-decision').forEach(btn => {
            btn.addEventListener('click', () => deleteDecision(btn.dataset.id));
        });
    }

    if (hasNotes) {
        searchNotesList.innerHTML = rs.notes.map(n => `
        <li class="note-item">
          <div class="note-header">
            <span class="note-title">${esc(n.title)}</span>
            <div class="header-actions">
              <button class="icon-btn edit-note" data-id="${n.id}">✎</button>
              <button class="icon-btn danger delete-note" data-id="${n.id}">🗑</button>
            </div>
            <span class="note-type-pill note-type-${n.note_type}">${n.note_type}</span>
          </div>
          <div class="note-text">${esc(n.note_text)}</div>
        </li>
      `).join('');

        searchNotesList.querySelectorAll('.edit-note').forEach(btn => {
            btn.addEventListener('click', () => {
                const note = rs.notes.find(n => n.id === btn.dataset.id);
                if (note) showNoteForm(note);
            });
        });
        searchNotesList.querySelectorAll('.delete-note').forEach(btn => {
            btn.addEventListener('click', () => deleteNote(btn.dataset.id));
        });
    }
}

// ── Filters ────────────────────────────────────────────────────────────────────
function bindFilters() {
    // Task status filters
    $('task-filters').addEventListener('click', e => {
        const btn = e.target.closest('.filter-btn');
        if (!btn) return;
        $('task-filters').querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.taskFilter = btn.dataset.status;
        renderTasks();
    });

    // Decision status filters
    $('decision-filters').addEventListener('click', e => {
        const btn = e.target.closest('.filter-btn');
        if (!btn) return;
        $('decision-filters').querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.decisionFilter = btn.dataset.status;
        renderDecisions();
    });

    // Note type filters
    $('note-filters').addEventListener('click', e => {
        const btn = e.target.closest('.filter-btn');
        if (!btn) return;
        $('note-filters').querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.noteFilter = btn.dataset.type;
        renderNotes();
    });
}

// ── Tasks ──────────────────────────────────────────────────────────────────────
function renderTasks() {
    const filtered = state.taskFilter
        ? state.tasks.filter(t => t.status === state.taskFilter)
        : state.tasks;

    if (!filtered.length) {
        taskListEl.innerHTML = '<li class="list-empty">No tasks found.</li>';
        return;
    }

    taskListEl.innerHTML = filtered.map(task => renderTaskItem(task)).join('');

    // Bind expand/collapse toggles
    taskListEl.querySelectorAll('.task-toggle').forEach(btn => {
        btn.addEventListener('click', e => {
            e.stopPropagation();
            const id = btn.dataset.taskId;
            const isExpanded = state.expandedTasks.has(id);
            if (isExpanded) {
                state.expandedTasks.delete(id);
            } else {
                state.expandedTasks.add(id);
            }
            const nowExpanded = !isExpanded;
            const body = document.getElementById(`task-body-${id}`);
            const subs = document.getElementById(`subtasks-${id}`);
            if (body) body.classList.toggle('hidden', !nowExpanded);
            if (subs) subs.classList.toggle('hidden', !nowExpanded);
            btn.classList.toggle('open', nowExpanded);
        });
    });

    taskListEl.querySelectorAll('.edit-task').forEach(btn => {
        btn.addEventListener('click', e => {
            e.stopPropagation();
            const id = btn.dataset.id;
            const task = findTask(id, state.tasks);
            if (task) showTaskForm(task);
        });
    });

    taskListEl.querySelectorAll('.delete-task').forEach(btn => {
        btn.addEventListener('click', e => {
            e.stopPropagation();
            deleteTask(btn.dataset.id);
        });
    });
}

function findTask(id, tasks) {
    for (const t of tasks) {
        if (t.id === id) return t;
        if (t.subtasks) {
            const found = findTask(id, t.subtasks);
            if (found) return found;
        }
    }
    return null;
}

function renderTaskItem(task, depth = 0) {
    const MAX_DEPTH = 5;
    const hasSubtasks = task.subtasks && task.subtasks.length > 0;
    const hasDesc = Boolean(task.description);
    const hasToggle = hasDesc || hasSubtasks;
    const expanded = state.expandedTasks.has(task.id);
    const statusIcon = statusEmoji(task.status);

    const blockedBadge = task.blocked_by_task_id
        ? `<span class="blocked-by-badge" title="Blocked by: ${task.blocked_by_task_id}">depends on</span>`
        : '';

    const nextAction = task.next_action
        ? `<div class="task-next-action">${esc(task.next_action)}</div>`
        : '';

    const toggle = hasToggle
        ? `<span class="task-toggle${expanded ? ' open' : ''}" data-task-id="${task.id}" title="Expand">›</span>`
        : '';

    // Description-only body (no subtasks here — they appear as siblings below the card)
    const bodyHtml = hasDesc
        ? `<div id="task-body-${task.id}" class="task-body${expanded ? '' : ' hidden'}">
             <div class="task-description markdown-body">${marked.parse(task.description)}</div>
           </div>`
        : '';

    // Subtasks rendered as a sibling list below the card, not inside the body
    const subtasksHtml = (hasSubtasks && depth < MAX_DEPTH)
        ? `<ul id="subtasks-${task.id}" class="subtask-list${expanded ? '' : ' hidden'}">
             ${task.subtasks.map(st => renderTaskItem(st, depth + 1)).join('')}
           </ul>`
        : '';

    const urgentBadge = task.urgent
        ? `<span class="urgent-dot" title="Urgent"></span>`
        : '';

    return `
    <li class="task-group" data-depth="${depth}">
      <div class="task-item ${task.status}">
        <div class="task-header">
          ${urgentBadge}
          <div class="task-title-area">
            <div class="task-title">${statusIcon} ${esc(task.title)}</div>
            <div class="task-meta">
              <span class="status-badge badge-${task.status}">${task.status}</span>
              ${blockedBadge}
              ${task.assigned_agent ? `<span style="font-size:10px;color:var(--text-muted)">[${esc(task.assigned_agent)}]</span>` : ''}
            </div>
            ${nextAction}
          </div>
          <div class="header-actions">
            <button class="icon-btn edit-task" data-id="${task.id}">✎</button>
            <button class="icon-btn danger delete-task" data-id="${task.id}">🗑</button>
          </div>
          ${toggle}
        </div>
        ${bodyHtml}
      </div>
      ${subtasksHtml}
    </li>`;
}

// ── Decisions ──────────────────────────────────────────────────────────────────
function renderDecisions() {
    const filtered = state.decisionFilter
        ? state.decisions.filter(d => d.status === state.decisionFilter)
        : state.decisions;

    if (!filtered.length) {
        decisionListEl.innerHTML = '<li class="list-empty">No decisions found.</li>';
        return;
    }

    decisionListEl.innerHTML = filtered.map(d => `
    <li class="decision-item ${d.status === 'superseded' ? 'superseded' : ''}">
      <div class="decision-header">
        <span class="decision-title">${esc(d.title)}</span>
        <div class="header-actions">
          <button class="icon-btn edit-decision" data-id="${d.id}">✎</button>
          <button class="icon-btn danger delete-decision" data-id="${d.id}">🗑</button>
        </div>
        <span class="status-badge badge-${d.status}">${d.status}</span>
      </div>
      <div class="decision-text markdown-body">${marked.parse(d.decision_text)}</div>
      ${d.rationale ? `<div class="decision-rationale">${esc(d.rationale)}</div>` : ''}
      ${d.supersedes_decision_id ? `<div style="font-size:11px;color:var(--text-muted);margin-top:6px">↳ Supersedes ${d.supersedes_decision_id.slice(0, 8)}</div>` : ''}
    </li>
  `).join('');

    decisionListEl.querySelectorAll('.edit-decision').forEach(btn => {
        btn.addEventListener('click', () => {
            const dec = state.decisions.find(d => d.id === btn.dataset.id);
            if (dec) showDecisionForm(dec);
        });
    });
    decisionListEl.querySelectorAll('.delete-decision').forEach(btn => {
        btn.addEventListener('click', () => deleteDecision(btn.dataset.id));
    });
}

async function deleteDecision(id) {
    if (!confirm('Delete this decision?')) return;
    try {
        await api.delete(`/api/projects/${state.activeProjectId}/decisions/${id}`);
        await selectProject(state.activeProjectId);
    } catch (err) {
        alert(err.message);
    }
}

// ── Notes ──────────────────────────────────────────────────────────────────────
function renderNotes() {
    const notes = state.notes || [];
    const filtered = state.noteFilter
        ? notes.filter(n => n.note_type === state.noteFilter)
        : notes;

    if (!filtered.length) {
        noteListEl.innerHTML = '<li class="list-empty">No notes found.</li>';
        return;
    }

    noteListEl.innerHTML = filtered.map(n => `
    <li class="note-item">
      <div class="note-header">
        <span class="note-title">${esc(n.title)}</span>
        <div class="header-actions">
          <button class="icon-btn edit-note" data-id="${n.id}">✎</button>
          <button class="icon-btn danger delete-note" data-id="${n.id}">🗑</button>
        </div>
        <span class="note-type-pill note-type-${n.note_type}">${n.note_type}</span>
      </div>
      <div class="note-text markdown-body">${marked.parse(n.note_text)}</div>
    </li>
  `).join('');

    noteListEl.querySelectorAll('.edit-note').forEach(btn => {
        btn.addEventListener('click', () => {
            const note = state.notes.find(n => n.id === btn.dataset.id);
            if (note) showNoteForm(note);
        });
    });
    noteListEl.querySelectorAll('.delete-note').forEach(btn => {
        btn.addEventListener('click', () => deleteNote(btn.dataset.id));
    });
}

// ── Timeline ───────────────────────────────────────────────────────────────────
function renderTimeline() {
    if (!state.timeline.length) {
        timelineListEl.innerHTML = '<li class="list-empty">No events yet.</li>';
        return;
    }

    timelineListEl.innerHTML = state.timeline.map(ev => `
    <li class="timeline-item">
      <div class="timeline-dot"></div>
      <div class="timeline-content">
        <div class="timeline-event-type">${esc(ev.event_type)}</div>
        <div class="timeline-task-title">${esc(ev.task_title)}</div>
        ${ev.event_note ? `<div class="timeline-note">${esc(ev.event_note)}</div>` : ''}
      </div>
      <div class="timeline-time">${formatTime(ev.created_at)}</div>
    </li>
  `).join('');
}

// ── Helpers ────────────────────────────────────────────────────────────────────
function esc(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function statusEmoji(status) {
    const map = {
        open: '○',
        in_progress: '◑',
        blocked: '⊗',
        done: '✓',
        cancelled: '✕',
    };
    return map[status] || '○';
}

function formatTime(iso) {
    if (!iso) return '';
    try {
        const d = new Date(iso);
        const now = new Date();
        const diffMs = now - d;
        const diffMins = Math.floor(diffMs / 60000);
        if (diffMins < 1) return 'just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours}h ago`;
        const diffDays = Math.floor(diffHours / 24);
        if (diffDays < 7) return `${diffDays}d ago`;
        return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    } catch {
        return iso.slice(0, 10);
    }
}

// ── Boot ───────────────────────────────────────────────────────────────────────
init();
