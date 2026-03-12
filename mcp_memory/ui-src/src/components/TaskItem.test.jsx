import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { AppProvider } from '../context/AppContext';
import TaskItem from './TaskItem';

const mockTask = {
  id: 't1',
  title: 'Test task',
  status: 'open',
  description: 'A task description',
  urgent: false,
  subtasks: [],
  notes: [],
};

function renderTaskItem(props = {}) {
  return render(
    <MemoryRouter>
      <AppProvider>
        <TaskItem
          task={mockTask}
          projectId="p1"
          depth={0}
          onRefresh={vi.fn()}
          {...props}
        />
      </AppProvider>
    </MemoryRouter>,
  );
}

describe('TaskItem', () => {
  it('collapsed: shows title, status badge, toggle arrow', () => {
    renderTaskItem();

    expect(screen.getByText('Test task')).toBeInTheDocument();
    const badge = screen.getByTestId('task-item-t1').querySelector('.status-badge');
    expect(badge).toHaveTextContent('open');
    // Collapsed arrow
    expect(screen.getByLabelText('Expand task')).toBeInTheDocument();
  });

  it('click toggle expands the task', async () => {
    const user = userEvent.setup();
    renderTaskItem();

    await user.click(screen.getByLabelText('Expand task'));

    // Now should show collapse label
    expect(screen.getByLabelText('Collapse task')).toBeInTheDocument();
    // Description should be visible
    expect(screen.getByText('A task description')).toBeInTheDocument();
  });

  it('shows urgent badge when task is urgent', () => {
    renderTaskItem({ task: { ...mockTask, urgent: true } });
    expect(screen.getByText('urgent')).toBeInTheDocument();
  });

  it('expanded: shows status dropdown and action buttons', async () => {
    const user = userEvent.setup();
    renderTaskItem();

    await user.click(screen.getByLabelText('Expand task'));

    expect(screen.getByText('Edit')).toBeInTheDocument();
    expect(screen.getByText('Delete')).toBeInTheDocument();
    expect(screen.getByText('Add Subtask')).toBeInTheDocument();
    // Status dropdown trigger
    const triggers = screen.getAllByRole('button');
    const statusTrigger = triggers.find((b) => b.classList.contains('task-status-trigger'));
    expect(statusTrigger).toBeTruthy();
  });
});
