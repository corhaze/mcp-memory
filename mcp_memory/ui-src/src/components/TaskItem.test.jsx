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
  it('collapsed: shows title, status, and toggle arrow', () => {
    renderTaskItem();

    expect(screen.getByText('Test task')).toBeInTheDocument();
    // Status dropdown trigger visible in header
    const triggers = screen.getAllByRole('button');
    const statusTrigger = triggers.find((b) => b.classList.contains('task-status-trigger'));
    expect(statusTrigger).toBeTruthy();
    // Toggle arrow
    const toggle = screen.getByTestId('task-item-t1').querySelector('.task-toggle');
    expect(toggle).toBeInTheDocument();
  });

  it('click toggle expands the task', async () => {
    const user = userEvent.setup();
    renderTaskItem();

    const toggle = screen.getByTestId('task-item-t1').querySelector('.task-toggle');
    await user.click(toggle);

    // Should show expanded toggle
    expect(toggle).toHaveClass('open');
    // Description should be visible
    expect(screen.getByText('A task description')).toBeInTheDocument();
  });

  it('shows urgent dot when task is urgent', () => {
    renderTaskItem({ task: { ...mockTask, urgent: true } });
    const urgentDot = screen.getByTestId('task-item-t1').querySelector('.urgent-dot');
    expect(urgentDot).toBeInTheDocument();
  });

  it('expanded: shows status dropdown and icon action buttons', async () => {
    const user = userEvent.setup();
    renderTaskItem();

    const toggle = screen.getByTestId('task-item-t1').querySelector('.task-toggle');
    await user.click(toggle);

    // Icon buttons for edit and delete
    expect(screen.getByTitle('Edit')).toBeInTheDocument();
    expect(screen.getByTitle('Delete')).toBeInTheDocument();
    // Add subtask button
    expect(screen.getByText('+ Add subtask')).toBeInTheDocument();
    // Status dropdown trigger
    const triggers = screen.getAllByRole('button');
    const statusTrigger = triggers.find((b) => b.classList.contains('task-status-trigger'));
    expect(statusTrigger).toBeTruthy();
  });
});
