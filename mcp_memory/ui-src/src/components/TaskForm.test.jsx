import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TaskForm from './TaskForm';

vi.mock('../api');
import * as api from '../api';

beforeEach(() => {
  vi.clearAllMocks();
});

describe('TaskForm', () => {
  it('create mode: empty fields', () => {
    render(
      <TaskForm projectId="p1" task={null} onSuccess={vi.fn()} onCancel={vi.fn()} />,
    );

    expect(screen.getByLabelText('Title')).toHaveValue('');
    expect(screen.getByLabelText('Description')).toHaveValue('');
    expect(screen.getByText(/open/)).toBeInTheDocument();
    expect(screen.getByText('Create Task')).toBeInTheDocument();
  });

  it('create mode: submit calls createTask with form data', async () => {
    const user = userEvent.setup();
    const onSuccess = vi.fn();
    api.createTask.mockResolvedValue({ id: 't1' });

    render(
      <TaskForm projectId="p1" task={null} onSuccess={onSuccess} onCancel={vi.fn()} />,
    );

    await user.type(screen.getByLabelText('Title'), 'New task');
    await user.type(screen.getByLabelText('Description'), 'Task details');
    await user.click(screen.getByText('Create Task'));

    expect(api.createTask).toHaveBeenCalledWith('p1', expect.objectContaining({
      title: 'New task',
      description: 'Task details',
      status: 'open',
    }));
    expect(onSuccess).toHaveBeenCalled();
  });

  it('edit mode: pre-filled fields from task object', () => {
    const task = {
      id: 't1',
      title: 'Existing task',
      description: 'Existing desc',
      status: 'in_progress',
      urgent: true,
      complex: false,
      blocked_by_task_id: null,
      next_action: 'Review',
    };

    render(
      <TaskForm projectId="p1" task={task} onSuccess={vi.fn()} onCancel={vi.fn()} />,
    );

    expect(screen.getByLabelText('Title')).toHaveValue('Existing task');
    expect(screen.getByLabelText('Description')).toHaveValue('Existing desc');
    expect(screen.getByText(/in_progress/)).toBeInTheDocument();
    expect(screen.getByText('Update Task')).toBeInTheDocument();
  });

  it('cancel calls onCancel', async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();

    render(
      <TaskForm projectId="p1" task={null} onSuccess={vi.fn()} onCancel={onCancel} />,
    );

    await user.click(screen.getByText('Cancel'));
    expect(onCancel).toHaveBeenCalled();
  });

  it('title required: does not submit without it', async () => {
    const user = userEvent.setup();
    api.createTask.mockResolvedValue({ id: 't1' });

    render(
      <TaskForm projectId="p1" task={null} onSuccess={vi.fn()} onCancel={vi.fn()} />,
    );

    await user.click(screen.getByText('Create Task'));
    expect(api.createTask).not.toHaveBeenCalled();
  });
});
