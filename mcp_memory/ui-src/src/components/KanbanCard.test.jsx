import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import KanbanCard from './KanbanCard';

const mockTask = {
  id: 't1',
  title: 'Build feature',
  status: 'open',
  urgent: false,
  next_action: null,
};

function renderCard(props = {}) {
  return render(
    <KanbanCard
      task={mockTask}
      onClick={vi.fn()}
      {...props}
    />,
  );
}

describe('KanbanCard', () => {
  it('renders the task title', () => {
    renderCard();
    expect(screen.getByText('Build feature')).toBeInTheDocument();
  });

  it('has draggable attribute', () => {
    renderCard();
    const card = screen.getByTestId('kanban-card-t1');
    expect(card).toHaveAttribute('draggable', 'true');
  });

  it('shows urgent dot when task.urgent is true', () => {
    renderCard({ task: { ...mockTask, urgent: true } });
    const urgentDot = screen.getByTestId('kanban-card-t1').querySelector('.urgent-dot');
    expect(urgentDot).toBeInTheDocument();
  });

  it('does not show urgent dot when task.urgent is false', () => {
    renderCard();
    const urgentDot = screen.getByTestId('kanban-card-t1').querySelector('.urgent-dot');
    expect(urgentDot).not.toBeInTheDocument();
  });

  it('shows complex badge when task.complex is true', () => {
    renderCard({ task: { ...mockTask, complex: true } });
    expect(screen.getByText('COMPLEX')).toBeInTheDocument();
  });

  it('shows subtask count when subtasks exist', () => {
    renderCard({
      task: {
        ...mockTask,
        subtasks: [
          { id: 's1', status: 'done' },
          { id: 's2', status: 'open' },
        ],
      },
    });
    expect(screen.getByText('1/2')).toBeInTheDocument();
  });
});
