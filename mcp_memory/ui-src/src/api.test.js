import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  getProjects,
  createTask,
  updateTask,
  deleteProject,
  semanticSearch,
} from './api';

function mockFetchOk(data) {
  return vi.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve(data),
    })
  );
}

function mockFetchError(status, detail) {
  return vi.fn(() =>
    Promise.resolve({
      ok: false,
      status,
      statusText: 'Not Found',
      json: () => Promise.resolve({ detail }),
    })
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe('api', () => {
  it('getProjects calls correct URL and returns data', async () => {
    const projects = [{ id: '1', name: 'test' }];
    vi.stubGlobal('fetch', mockFetchOk(projects));
    const result = await getProjects();
    expect(fetch).toHaveBeenCalledWith('/api/projects', { method: 'GET' });
    expect(result).toEqual(projects);
  });

  it('createTask sends POST with body', async () => {
    const task = { id: 't1', title: 'Do something' };
    vi.stubGlobal('fetch', mockFetchOk(task));
    const body = { title: 'Do something' };
    const result = await createTask('p1', body);
    expect(fetch).toHaveBeenCalledWith('/api/projects/p1/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    expect(result).toEqual(task);
  });

  it('updateTask sends PATCH with body', async () => {
    const updated = { id: 't1', status: 'done' };
    vi.stubGlobal('fetch', mockFetchOk(updated));
    const body = { status: 'done' };
    await updateTask('p1', 't1', body);
    expect(fetch).toHaveBeenCalledWith('/api/projects/p1/tasks/t1', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  });

  it('deleteProject sends DELETE', async () => {
    vi.stubGlobal('fetch', mockFetchOk({ ok: true }));
    await deleteProject('p1');
    expect(fetch).toHaveBeenCalledWith('/api/projects/p1', { method: 'DELETE' });
  });

  it('throws with error detail on non-ok response', async () => {
    vi.stubGlobal('fetch', mockFetchError(404, 'Project not found'));
    await expect(getProjects()).rejects.toThrow('Project not found');
  });

  it('semanticSearch builds correct query string', async () => {
    vi.stubGlobal('fetch', mockFetchOk([]));
    await semanticSearch('hello world', 'p1');
    const url = fetch.mock.calls[0][0];
    expect(url).toContain('/api/search/semantic?');
    expect(url).toContain('q=hello+world');
    expect(url).toContain('project_id=p1');
  });

  it('semanticSearch works without projectId', async () => {
    vi.stubGlobal('fetch', mockFetchOk([]));
    await semanticSearch('test');
    const url = fetch.mock.calls[0][0];
    expect(url).toContain('q=test');
    expect(url).not.toContain('project_id');
  });
});
