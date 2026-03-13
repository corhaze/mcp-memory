import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
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

const mockTaskWithSubtaskDetails = {
  ...mockTask,
  subtasks: [
    {
      id: 't2',
      title: 'Subtask 1',
      status: 'done',
      description: 'Subtask description text',
      next_action: 'Do the next thing',
    },
  ],
};

const mockTaskWithSubtaskNoDetails = {
  ...mockTask,
  subtasks: [
    { id: 't2', title: 'Subtask 1', status: 'done' },
  ],
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
    const statusTrigger = screen.getByTestId('task-detail').querySelector('.task-status-trigger');
    expect(statusTrigger).toHaveTextContent('open');
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

  describe('subtask accordion expansion', () => {
    it('toggle arrow click expands the subtask body', () => {
      useTask.mockReturnValue({ task: mockTaskWithSubtaskDetails, loading: false, error: null, refresh: vi.fn() });
      useProjects.mockReturnValue({ projects: mockProjects, loading: false, error: null, refresh: vi.fn() });

      renderTaskDetail();

      expect(screen.queryByText('Subtask description text')).not.toBeInTheDocument();
      fireEvent.click(screen.getByRole('button', { name: '›' }));
      expect(screen.getByText('Subtask description text')).toBeInTheDocument();
    });

    it('toggle arrow click again collapses the subtask body', () => {
      useTask.mockReturnValue({ task: mockTaskWithSubtaskDetails, loading: false, error: null, refresh: vi.fn() });
      useProjects.mockReturnValue({ projects: mockProjects, loading: false, error: null, refresh: vi.fn() });

      renderTaskDetail();

      const toggleBtn = screen.getByRole('button', { name: '›' });
      fireEvent.click(toggleBtn);
      expect(screen.getByText('Subtask description text')).toBeInTheDocument();
      fireEvent.click(toggleBtn);
      expect(screen.queryByText('Subtask description text')).not.toBeInTheDocument();
    });

    it('subtask title link has correct href', () => {
      useTask.mockReturnValue({ task: mockTask, loading: false, error: null, refresh: vi.fn() });
      useProjects.mockReturnValue({ projects: mockProjects, loading: false, error: null, refresh: vi.fn() });

      renderTaskDetail();

      const titleLink = screen.getByText('Subtask 1').closest('a');
      expect(titleLink).toHaveAttribute('href', '/my-project/tasks/t2');
    });

    it('expansion shows description and next_action when present', () => {
      useTask.mockReturnValue({ task: mockTaskWithSubtaskDetails, loading: false, error: null, refresh: vi.fn() });
      useProjects.mockReturnValue({ projects: mockProjects, loading: false, error: null, refresh: vi.fn() });

      renderTaskDetail();

      fireEvent.click(screen.getByRole('button', { name: '›' }));
      expect(screen.getByText('Subtask description text')).toBeInTheDocument();
      expect(screen.getByText('Do the next thing')).toBeInTheDocument();
    });

    it('no expansion body rendered when no description and no next_action', () => {
      useTask.mockReturnValue({ task: mockTaskWithSubtaskNoDetails, loading: false, error: null, refresh: vi.fn() });
      useProjects.mockReturnValue({ projects: mockProjects, loading: false, error: null, refresh: vi.fn() });

      renderTaskDetail();

      fireEvent.click(screen.getByRole('button', { name: '›' }));
      const container = screen.getByTestId('task-detail');
      expect(container.querySelector('.subtask-expand-body')).not.toBeInTheDocument();
    });
  });
});
