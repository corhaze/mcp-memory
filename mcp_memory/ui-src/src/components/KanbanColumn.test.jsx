import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import KanbanColumn from './KanbanColumn';

const mockTasks = [
  { id: 't1', title: 'Task one', status: 'open', urgent: false },
  { id: 't2', title: 'Task two', status: 'open', urgent: false },
];

function renderColumn(props = {}) {
  return render(
    <KanbanColumn
      status="open"
      title="Open"
      tasks={mockTasks}
      onDrop={vi.fn()}
      onCardClick={vi.fn()}
      {...props}
    />,
  );
}

describe('KanbanColumn', () => {
  it('renders header with title and count', () => {
    renderColumn();
    expect(screen.getByText('Open')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('renders a card for each task', () => {
    renderColumn();
    expect(screen.getByTestId('kanban-card-t1')).toBeInTheDocument();
    expect(screen.getByTestId('kanban-card-t2')).toBeInTheDocument();
  });

  it('renders zero count for empty column', () => {
    renderColumn({ tasks: [] });
    expect(screen.getByText('0')).toBeInTheDocument();
  });
});
