import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AppProvider } from '../context/AppContext';
import TaskDetail from './TaskDetail';

vi.mock('../hooks/useTask');
vi.mock('../hooks/useProjects');

import { useTask } from '../hooks/useTask';
import { useProjects } from '../hooks/useProjects';

beforeEach(() => {
  vi.clearAllMocks();
});

const mockTask = {
  id: 't1',
  title: 'Test task detail',
  description: 'Detailed description here',
  status: 'open',
  urgent: false,
  subtasks: [
    { id: 't2', title: 'Subtask 1', status: 'done' },
  ],
  notes: [],
  events: [],
  parent_task_id: null,
  blocked_by_task_id: null,
};

const mockProjects = [
  { id: 'p1', name: 'my-project', status: 'active' },
];

function renderTaskDetail(path = '/my-project/tasks/t1') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppProvider>
        <Routes>
          <Route path=":projectName/tasks/:taskId" element={<TaskDetail />} />
          <Route path=":projectName/tasks" element={<div>Tasks list</div>} />
        </Routes>
      </AppProvider>
    </MemoryRouter>,
  );
}

describe('TaskDetail', () => {
  it('renders task title, description, status', () => {
    useTask.mockReturnValue({ task: mockTask, loading: false, error: null, refresh: vi.fn() });
    useProjects.mockReturnValue({ projects: mockProjects, loading: false, error: null, refresh: vi.fn() });

    renderTaskDetail();

    expect(screen.getByText('Test task detail')).toBeInTheDocument();
    expect(screen.getByText('Detailed description here')).toBeInTheDocument();
    const statusBadge = screen.getByTestId('task-detail').querySelector('.status-badge');
    expect(statusBadge).toHaveTextContent('open');
  });

  it('back link present', () => {
    useTask.mockReturnValue({ task: mockTask, loading: false, error: null, refresh: vi.fn() });
    useProjects.mockReturnValue({ projects: mockProjects, loading: false, error: null, refresh: vi.fn() });

    renderTaskDetail();

    const backLink = screen.getByText(/Back to Tasks/);
    expect(backLink).toBeInTheDocument();
    expect(backLink.closest('a')).toHaveAttribute('href', '/my-project/tasks');
  });

  it('shows subtask list', () => {
    useTask.mockReturnValue({ task: mockTask, loading: false, error: null, refresh: vi.fn() });
    useProjects.mockReturnValue({ projects: mockProjects, loading: false, error: null, refresh: vi.fn() });

    renderTaskDetail();

    expect(screen.getByText('Subtasks')).toBeInTheDocument();
    expect(screen.getByText(/Subtask 1/)).toBeInTheDocument();
  });

  it('shows loading state', () => {
    useTask.mockReturnValue({ task: null, loading: true, error: null, refresh: vi.fn() });
    useProjects.mockReturnValue({ projects: mockProjects, loading: false, error: null, refresh: vi.fn() });

    renderTaskDetail();

    expect(screen.getByText('Loading task...')).toBeInTheDocument();
  });

  it('shows error state', () => {
    useTask.mockReturnValue({ task: null, loading: false, error: 'Not found', refresh: vi.fn() });
    useProjects.mockReturnValue({ projects: mockProjects, loading: false, error: null, refresh: vi.fn() });

    renderTaskDetail();

    expect(screen.getByText('Error: Not found')).toBeInTheDocument();
  });
});
