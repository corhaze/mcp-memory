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

  it('shows urgent badge when task.urgent is true', () => {
    renderCard({ task: { ...mockTask, urgent: true } });
    expect(screen.getByText('urgent')).toBeInTheDocument();
  });

  it('does not show urgent badge when task.urgent is false', () => {
    renderCard();
    expect(screen.queryByText('urgent')).not.toBeInTheDocument();
  });

  it('shows truncated next_action', () => {
    const longAction = 'A'.repeat(100);
    renderCard({ task: { ...mockTask, next_action: longAction } });
    expect(screen.getByText('A'.repeat(80) + '...')).toBeInTheDocument();
  });
});
