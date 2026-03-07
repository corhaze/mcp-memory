let currentProject = '';
let currentTab = 'context';
let projectToDelete = '';

async function fetchProjects() {
    try {
        const response = await fetch('/api/projects');
        const projects = await response.json();
        const list = document.getElementById('projectList');
        list.innerHTML = '';

        projects.forEach(p => {
            const li = document.createElement('li');
            li.className = 'project-item';
            if (p === currentProject) li.classList.add('active');

            const nameSpan = document.createElement('span');
            nameSpan.textContent = p;
            nameSpan.onclick = () => selectProject(p);

            const deleteBtn = document.createElement('div');
            deleteBtn.className = 'delete-btn';
            deleteBtn.innerHTML = '×';
            deleteBtn.title = 'Delete project';
            deleteBtn.onclick = (e) => {
                e.stopPropagation();
                openDeleteModal(p);
            };

            li.appendChild(nameSpan);
            li.appendChild(deleteBtn);
            list.appendChild(li);
        });

        if (projects.length > 0 && !currentProject) {
            selectProject(projects[0]);
        } else if (projects.length === 0) {
            document.getElementById('contentViewer').innerHTML = '<div class="card">No projects found.</div>';
            document.getElementById('currentProjectLabel').textContent = '';
        }
    } catch (err) {
        console.error('Failed to fetch projects:', err);
    }
}

function selectProject(projectName) {
    currentProject = projectName;
    document.getElementById('currentProjectLabel').textContent = projectName;

    // Update active state in sidebar
    const items = document.querySelectorAll('.project-item');
    items.forEach(item => {
        const span = item.querySelector('span');
        item.classList.toggle('active', span.textContent === projectName);
    });

    loadData();
}

function switchTab(tab) {
    currentTab = tab;
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(t => {
        t.classList.toggle('active', t.textContent.toLowerCase() === tab);
    });
    loadData();
}

async function loadData() {
    if (!currentProject) return;
    const viewer = document.getElementById('contentViewer');
    viewer.innerHTML = '<div class="card">Loading...</div>';

    try {
        let url = '';
        if (currentTab === 'context') {
            url = `/api/project/${currentProject}/context`;
        } else if (currentTab === 'timeline') {
            url = `/api/project/${currentProject}/timeline`;
        } else if (currentTab === 'insights') {
            url = `/api/insights?scope=${currentProject}`;
        } else if (currentTab === 'todos') {
            url = `/api/project/${currentProject}/todos`;
        }

        const response = await fetch(url);
        const data = await response.json();

        renderData(data);
    } catch (err) {
        viewer.innerHTML = `<div class="card" style="color: var(--accent-color)">Error loading data: ${err.message}</div>`;
    }
}

function renderData(data) {
    const viewer = document.getElementById('contentViewer');
    viewer.innerHTML = '';

    if (!data || data.length === 0) {
        viewer.innerHTML = '<div class="card">No entries found.</div>';
        return;
    }

    data.forEach(item => {
        const card = document.createElement('div');
        card.className = 'card';

        if (currentTab === 'context') {
            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem">
                    <span class="badge">${item.category}</span>
                    <span style="font-size: 0.8rem; color: var(--text-secondary)">${item.key}</span>
                </div>
                <div style="font-size: 1.1rem; line-height: 1.6">${formatValue(item.value)}</div>
                ${renderTags(item.tags)}
            `;
        } else if (currentTab === 'timeline') {
            card.innerHTML = `
                <div style="display: flex; align-items: center; margin-bottom: 0.5rem">
                    <span class="event-type type-${item.event_type}">${item.event_type}</span>
                    <span style="font-size: 0.8rem; color: var(--text-secondary)">${new Date(item.timestamp).toLocaleString()}</span>
                </div>
                <div style="font-weight: 500; font-size: 1.1rem; margin-bottom: 0.5rem">${item.summary}</div>
                ${item.detail ? `<div style="color: var(--text-secondary); line-height: 1.5">${item.detail}</div>` : ''}
            `;
        } else if (currentTab === 'insights') {
            card.innerHTML = `
                <div style="font-weight: 600; font-size: 1.2rem; margin-bottom: 0.75rem">${item.title}</div>
                <div style="line-height: 1.6; color: var(--text-secondary)">${item.body}</div>
                ${renderTags(item.tags)}
            `;
        } else if (currentTab === 'todos') {
            let priorityColor = 'var(--text-secondary)';
            if (item.priority === 'high') priorityColor = '#ff5858';
            if (item.priority === 'medium') priorityColor = '#ffb340';

            let statusColor = 'var(--text-secondary)';
            if (item.status === 'completed') statusColor = '#3fb950';
            if (item.status === 'in_progress') statusColor = '#58a6ff';

            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem">
                    <div style="font-weight: 600; font-size: 1.2rem;">${item.title}</div>
                    <div style="display: flex; gap: 0.5rem; align-items: center;">
                        <span class="badge" style="background: ${statusColor}22; color: ${statusColor}; border: 1px solid ${statusColor}44">${item.status}</span>
                        <span class="badge" style="background: ${priorityColor}22; color: ${priorityColor}; border: 1px solid ${priorityColor}44">${item.priority}</span>
                    </div>
                </div>
                <div style="line-height: 1.6; color: var(--text-secondary)">${formatValue(item.description)}</div>
            `;
        }

        viewer.appendChild(card);
    });
}

function renderTags(tags) {
    if (!tags) return '';
    const tagList = Array.isArray(tags) ? tags : (typeof tags === 'string' ? tags.split(',') : []);
    if (tagList.length === 0) return '';

    return `<div style="margin-top: 1rem">${tagList.map(t => `<span class="badge" style="background: rgba(88, 166, 255, 0.1); color: var(--accent-color)">#${t.trim()}</span>`).join('')}</div>`;
}

function formatValue(val) {
    if (typeof val === 'string' && val.includes('\n')) {
        return `<pre>${val}</pre>`;
    }
    return val;
}

// Modal Functions
function openDeleteModal(projectName) {
    projectToDelete = projectName;
    document.getElementById('deleteProjectName').textContent = projectName;
    document.getElementById('deleteModal').style.display = 'block';
}

function closeModal() {
    document.getElementById('deleteModal').style.display = 'none';
    projectToDelete = '';
}

async function confirmDelete() {
    if (!projectToDelete) return;

    try {
        const response = await fetch(`/api/project/${projectToDelete}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            if (currentProject === projectToDelete) {
                currentProject = '';
            }
            closeModal();
            fetchProjects();
        } else {
            alert('Failed to delete project');
        }
    } catch (err) {
        console.error('Delete error:', err);
        alert('Error deleting project');
    }
}

// Initialize
fetchProjects();
