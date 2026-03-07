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
    taskFilter: '',
    decisionFilter: '',
    noteFilter: '',
    expandedTasks: new Set(),
};

// ── API ────────────────────────────────────────────────────────────────────────
const api = {
    async get(path) {
        const res = await fetch(path);
        if (!res.ok) throw new Error(`API ${path}: ${res.status}`);
        return res.json();
    },
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

// ── Routing ────────────────────────────────────────────────────────────────────
// URL format: /{project-name}/{tab}  e.g. /mcp-memory/decisions
const VALID_TABS = ['tasks', 'decisions', 'notes', 'timeline'];

function parsePath() {
    const parts = location.pathname.replace(/^\//, '').split('/').filter(Boolean);
    if (!parts.length) return null;
    const projectName = decodeURIComponent(parts[0]);
    const tab = VALID_TABS.includes(parts[1]) ? parts[1] : 'tasks';
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
                await selectProject(proj.id, s.tab || 'tasks', { updatePath: false });
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

async function selectProject(id, tab = 'tasks', { updatePath = true } = {}) {
    state.activeProjectId = id;
    state.expandedTasks.clear();

    // Update nav highlight
    document.querySelectorAll('.project-nav-item').forEach(b => {
        b.classList.toggle('active', b.dataset.id === id);
    });

    // Show project view, hide empty state
    emptyState.classList.add('hidden');
    projectView.classList.remove('hidden');

    // Load all data in parallel
    const [ctx, tasks, decisions, notes, timeline] = await Promise.all([
        api.get(`/api/projects/${id}`),
        api.get(`/api/projects/${id}/tasks?topo=true`),
        api.get(`/api/projects/${id}/decisions`),
        api.get(`/api/projects/${id}/notes`),
        api.get(`/api/projects/${id}/timeline`),
    ]);

    state.tasks = tasks;
    state.decisions = decisions;
    state.notes = notes;
    state.timeline = timeline;

    // Render header
    const proj = ctx.project || {};
    projectName.textContent = proj.name || id;
    projectDesc.textContent = proj.description || '';
    projectStatus.textContent = proj.status || '';
    projectStatus.className = `status-badge badge-${proj.status || 'active'}`;
    projectSummary.textContent = ctx.summary || '';
    projectSummary.classList.toggle('hidden', !ctx.summary);

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
            const body = document.getElementById(`task-body-${id}`);
            if (!body) return;
            const isOpen = body.classList.toggle('hidden');
            btn.classList.toggle('open', !isOpen);
        });
    });
}

function renderTaskItem(task, depth = 0) {
    const MAX_DEPTH = 5;
    const hasSubtasks = task.subtasks && task.subtasks.length > 0;
    const hasBody = task.description || hasSubtasks;
    const expanded = state.expandedTasks.has(task.id);
    const statusIcon = statusEmoji(task.status);

    const blockedBadge = task.blocked_by_task_id
        ? `<span class="blocked-by-badge" title="Blocked by: ${task.blocked_by_task_id}">depends on</span>`
        : '';

    const nextAction = task.next_action
        ? `<div class="task-next-action">${esc(task.next_action)}</div>`
        : '';

    const subtaskHtml = (hasSubtasks && depth < MAX_DEPTH)
        ? `<ul class="subtask-list">${task.subtasks.map(st => renderTaskItem(st, depth + 1)).join('')}</ul>`
        : '';

    const toggle = hasBody
        ? `<span class="task-toggle${expanded ? ' open' : ''}" data-task-id="${task.id}" title="Expand">›</span>`
        : '';

    const descHtml = task.description
        ? `<div class="task-description">${esc(task.description)}</div>`
        : '';

    return `
    <li class="task-item ${task.status}" data-depth="${depth}" data-task-id="${task.id}">
      <div class="task-header">
        <span class="priority-dot priority-${task.priority || 'medium'}" title="${task.priority}"></span>
        <div class="task-title-area">
          <div class="task-title">${statusIcon} ${esc(task.title)}</div>
          <div class="task-meta">
            <span class="status-badge badge-${task.status}">${task.status}</span>
            ${blockedBadge}
            ${task.assigned_agent ? `<span style="font-size:10px;color:var(--text-muted)">[${esc(task.assigned_agent)}]</span>` : ''}
          </div>
          ${nextAction}
        </div>
        ${toggle}
      </div>
      ${hasBody ? `<div id="task-body-${task.id}" class="task-body${expanded ? '' : ' hidden'}">
        ${descHtml}
        ${subtaskHtml}
      </div>` : ''}
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
        <span class="status-badge badge-${d.status}">${d.status}</span>
      </div>
      <div class="decision-text">${esc(d.decision_text)}</div>
      ${d.rationale ? `<div class="decision-rationale">${esc(d.rationale)}</div>` : ''}
      ${d.supersedes_decision_id ? `<div style="font-size:11px;color:var(--text-muted);margin-top:6px">↳ Supersedes ${d.supersedes_decision_id.slice(0, 8)}</div>` : ''}
    </li>
  `).join('');
}

// ── Notes ──────────────────────────────────────────────────────────────────────
function renderNotes() {
    const filtered = state.noteFilter
        ? state.notes.filter(n => n.note_type === state.noteFilter)
        : state.notes;

    if (!filtered.length) {
        noteListEl.innerHTML = '<li class="list-empty">No notes found.</li>';
        return;
    }

    noteListEl.innerHTML = filtered.map(n => `
    <li class="note-item">
      <div class="note-header">
        <span class="note-title">${esc(n.title)}</span>
        <span class="note-type-pill note-type-${n.note_type}">${n.note_type}</span>
      </div>
      <div class="note-text">${esc(n.note_text)}</div>
    </li>
  `).join('');
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
