/* api.js — React API client for mcp-memory backend */

async function request(path, method = 'GET', body = null) {
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
}

// Projects
export const getProjects = () => request('/api/projects');
export const getProject = (id) => request(`/api/projects/${id}`);
export const createProject = (data) => request('/api/projects', 'POST', data);
export const updateProject = (id, data) => request(`/api/projects/${id}`, 'PATCH', data);
export const deleteProject = (id) => request(`/api/projects/${id}`, 'DELETE');

// Project Summary
// Note: summary is fetched via getProject() which returns { project, summary }.
// There is no separate GET endpoint for summary.
export const getProjectSummary = async (projectId) => {
  const data = await request(`/api/projects/${projectId}`);
  return data.summary ?? null;
};
export const updateProjectSummary = (projectId, summaryText) =>
  request(`/api/projects/${projectId}/summary`, 'POST', { summary_text: summaryText });

// Tasks
export const getProjectTasks = (projectId) =>
  request(`/api/projects/${projectId}/tasks?topo=true`);
export const createTask = (projectId, data) =>
  request(`/api/projects/${projectId}/tasks`, 'POST', data);
export const updateTask = (projectId, taskId, data) =>
  request(`/api/projects/${projectId}/tasks/${taskId}`, 'PATCH', data);
export const deleteTask = (projectId, taskId) =>
  request(`/api/projects/${projectId}/tasks/${taskId}`, 'DELETE');
export const getTask = (projectId, taskId) =>
  request(`/api/projects/${projectId}/tasks/${taskId}`);

// Task Notes
export const getTaskNotes = (taskId) => request(`/api/tasks/${taskId}/notes`);
export const createTaskNote = (taskId, data) =>
  request(`/api/tasks/${taskId}/notes`, 'POST', data);
export const deleteTaskNote = (noteId) =>
  request(`/api/task-notes/${noteId}`, 'DELETE');

// Decisions
export const getProjectDecisions = (projectId) =>
  request(`/api/projects/${projectId}/decisions`);
export const createDecision = (projectId, data) =>
  request(`/api/projects/${projectId}/decisions`, 'POST', data);
export const updateDecision = (projectId, decId, data) =>
  request(`/api/projects/${projectId}/decisions/${decId}`, 'PATCH', data);
export const deleteDecision = (projectId, decId) =>
  request(`/api/projects/${projectId}/decisions/${decId}`, 'DELETE');

// Notes
export const getProjectNotes = (projectId) =>
  request(`/api/projects/${projectId}/notes`);
export const createNote = (projectId, data) =>
  request(`/api/projects/${projectId}/notes`, 'POST', data);
export const updateNote = (projectId, noteId, data) =>
  request(`/api/projects/${projectId}/notes/${noteId}`, 'PATCH', data);
export const deleteNote = (projectId, noteId) =>
  request(`/api/projects/${projectId}/notes/${noteId}`, 'DELETE');

// Global Notes
export const getGlobalNotes = () => request('/api/global-notes');
export const getGlobalNote = (noteId) => request(`/api/global-notes/${noteId}`);
export const createGlobalNote = (data) => request('/api/global-notes', 'POST', data);
export const updateGlobalNote = (noteId, data) =>
  request(`/api/global-notes/${noteId}`, 'PATCH', data);
export const deleteGlobalNote = (noteId) =>
  request(`/api/global-notes/${noteId}`, 'DELETE');

// Timeline
export const getTimeline = (projectId) =>
  request(`/api/projects/${projectId}/timeline`);

// Search
export function semanticSearch(query, projectId) {
  const params = new URLSearchParams({ q: query });
  if (projectId) params.set('project_id', projectId);
  return request(`/api/search/semantic?${params}`);
}
