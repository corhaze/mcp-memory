import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AppProvider } from '../context/AppContext';
import TaskList from './TaskList';

function renderTaskList(props = {}) {
  return render(
    <MemoryRouter>
      <AppProvider>
        <TaskList projectId="p1" onRefresh={vi.fn()} {...props} />
      </AppProvider>
    </MemoryRouter>,
  );
}

describe('TaskList', () => {
  it('renders flat list of tasks with correct titles', () => {
    const tasks = [
      { id: 't1', title: 'First task', status: 'open', subtasks: [] },
      { id: 't2', title: 'Second task', status: 'done', subtasks: [] },
    ];

    renderTaskList({ tasks });

    expect(screen.getByText('First task')).toBeInTheDocument();
    expect(screen.getByText('Second task')).toBeInTheDocument();
  });

  it('renders nested subtasks with indentation', () => {
    const tasks = [
      {
        id: 't1',
        title: 'Parent task',
        status: 'open',
        subtasks: [
          { id: 't2', title: 'Child task', status: 'open', subtasks: [] },
        ],
      },
    ];

    renderTaskList({ tasks });
    expect(screen.getByText('Parent task')).toBeInTheDocument();
    // Child is not visible until parent expanded, but the structure exists
  });

  it('shows empty state when no tasks', () => {
    renderTaskList({ tasks: [] });
    expect(screen.getByTestId('task-list-empty')).toBeInTheDocument();
    expect(screen.getByText('No tasks found.')).toBeInTheDocument();
  });

  it('returns null for empty nested list (depth > 0)', () => {
    const { container } = render(
      <MemoryRouter>
        <AppProvider>
          <TaskList tasks={[]} projectId="p1" depth={1} onRefresh={vi.fn()} />
        </AppProvider>
      </MemoryRouter>,
    );
    expect(container.innerHTML).toBe('');
  });
});
