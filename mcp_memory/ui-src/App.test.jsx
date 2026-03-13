import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AppRoutes } from './App';
import { AppProvider } from './src/context/AppContext';

// Mock useProjects to avoid real API calls from Layout/Sidebar
vi.mock('./src/hooks/useProjects', () => ({
  useProjects: () => ({
    projects: [{ id: '1', name: 'some-project', status: 'active' }],
    loading: false,
    error: null,
    refresh: vi.fn(),
  }),
}));

// Mock useProjectData to avoid real API calls from ProjectView
vi.mock('./src/hooks/useProjectData', () => ({
  useProjectData: () => ({
    tasks: [],
    decisions: [],
    notes: [],
    timeline: [],
    summary: null,
    loading: false,
    error: null,
    refresh: vi.fn(),
    refreshTasks: vi.fn(),
  }),
}));

// Mock useTask to avoid real API calls from TaskDetail
vi.mock('./src/hooks/useTask', () => ({
  useTask: () => ({
    task: { id: 't1', title: 'Mock task', status: 'open', subtasks: [], notes: [], events: [] },
    loading: false,
    error: null,
    refresh: vi.fn(),
  }),
}));

// Mock API calls used by NoteDetail
vi.mock('./src/api', () => ({
  getGlobalNote: vi.fn(() => Promise.resolve({ id: 'abc', title: 'Test', note_text: 'Body', note_type: null })),
  getProjectNotes: vi.fn(() => Promise.resolve([{ id: 'n1', title: 'Test', note_text: 'Body', note_type: null }])),
  getProjects: vi.fn(() => Promise.resolve([])),
  getProjectTasks: vi.fn(() => Promise.resolve([])),
  getProjectDecisions: vi.fn(() => Promise.resolve([])),
  getTimeline: vi.fn(() => Promise.resolve([])),
  getProjectSummary: vi.fn(() => Promise.resolve(null)),
}));

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppProvider>
        <AppRoutes />
      </AppProvider>
    </MemoryRouter>,
  );
}

describe('Router', () => {
  it('renders empty state at /', () => {
    renderAt('/');
    expect(screen.getByTestId('empty-state')).toBeInTheDocument();
  });

  it('renders global workspace at /global', () => {
    renderAt('/global');
    expect(screen.getByTestId('global-workspace')).toBeInTheDocument();
  });

  it('renders note detail at /global/notes/abc', async () => {
    renderAt('/global/notes/abc');
    expect(await screen.findByTestId('note-detail')).toBeInTheDocument();
  });

  it('renders project view at /some-project', () => {
    renderAt('/some-project');
    expect(screen.getByTestId('project-view')).toBeInTheDocument();
  });

  it('renders project view at /some-project/tasks', () => {
    renderAt('/some-project/tasks');
    expect(screen.getByTestId('project-view')).toBeInTheDocument();
  });

  it('renders task detail at /some-project/tasks/t1', () => {
    renderAt('/some-project/tasks/t1');
    expect(screen.getByTestId('task-detail')).toBeInTheDocument();
  });

  it('renders note detail at /some-project/notes/n1', async () => {
    renderAt('/some-project/notes/n1');
    expect(await screen.findByTestId('note-detail')).toBeInTheDocument();
  });
});
