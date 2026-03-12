import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import KanbanBoard from './KanbanBoard';

vi.mock('../api', () => ({
  updateTask: vi.fn(() => Promise.resolve()),
}));

function makeTasks(statuses) {
  return statuses.map((status, i) => ({
    id: `t${i}`,
    title: `Task ${i}`,
    status,
    urgent: false,
    parent_task_id: null,
    created_at: `2026-01-0${i + 1}T00:00:00`,
  }));
}

function renderBoard(tasks = [], props = {}) {
  return render(
    <MemoryRouter>
      <KanbanBoard
        tasks={tasks}
        projectId="p1"
        projectName="test-project"
        onRefresh={vi.fn()}
        {...props}
      />
    </MemoryRouter>,
  );
}

describe('KanbanBoard', () => {
  it('renders 4 columns', () => {
    renderBoard();
    expect(screen.getByTestId('kanban-column-open')).toBeInTheDocument();
    expect(screen.getByTestId('kanban-column-in_progress')).toBeInTheDocument();
    expect(screen.getByTestId('kanban-column-blocked')).toBeInTheDocument();
    expect(screen.getByTestId('kanban-column-done')).toBeInTheDocument();
  });

  it('groups tasks by status', () => {
    const tasks = makeTasks(['open', 'open', 'in_progress', 'blocked', 'done']);
    renderBoard(tasks);

    const openCol = screen.getByTestId('kanban-column-open');
    const ipCol = screen.getByTestId('kanban-column-in_progress');
    const blockedCol = screen.getByTestId('kanban-column-blocked');
    const doneCol = screen.getByTestId('kanban-column-done');

    expect(openCol.querySelectorAll('.kanban-card')).toHaveLength(2);
    expect(ipCol.querySelectorAll('.kanban-card')).toHaveLength(1);
    expect(blockedCol.querySelectorAll('.kanban-card')).toHaveLength(1);
    expect(doneCol.querySelectorAll('.kanban-card')).toHaveLength(1);
  });

  it('limits done column to 5 tasks', () => {
    const tasks = makeTasks([
      'done', 'done', 'done', 'done', 'done', 'done', 'done',
    ]);
    renderBoard(tasks);

    const doneCol = screen.getByTestId('kanban-column-done');
    expect(doneCol.querySelectorAll('.kanban-card')).toHaveLength(5);
  });

  it('excludes subtasks (tasks with parent_task_id)', () => {
    const tasks = [
      { id: 't0', title: 'Parent', status: 'open', parent_task_id: null },
      { id: 't1', title: 'Child', status: 'open', parent_task_id: 't0' },
    ];
    renderBoard(tasks);

    const openCol = screen.getByTestId('kanban-column-open');
    expect(openCol.querySelectorAll('.kanban-card')).toHaveLength(1);
  });
});
