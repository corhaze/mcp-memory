import { marked } from 'marked';
import { useAppState, useAppDispatch } from '../context/AppContext';
import StatusBadge from './StatusBadge';
import StatusDropdown from './StatusDropdown';
import TaskForm from './TaskForm';
import TaskNoteList from './TaskNoteList';
import TaskNoteForm from './TaskNoteForm';
import TaskList from './TaskList';
import * as api from '../api';

export default function TaskItem({ task, projectId, depth = 0, onRefresh }) {
  const state = useAppState();
  const dispatch = useAppDispatch();

  const expanded = state.expandedTasks.has(task.id);
  const isEditing = state.editingTaskId === task.id;
  const showSubtaskForm = state.showAddSubtaskForm.has(task.id);
  const showNoteForm = state.showAddTaskNoteForm.has(task.id);
  const hasSubtasks = task.subtasks && task.subtasks.length > 0;

  function handleToggle(e) {
    e.stopPropagation();
    dispatch({ type: 'TOGGLE_TASK_EXPANDED', id: task.id });
  }

  async function handleStatusChange(newStatus) {
    await api.updateTask(projectId, task.id, { status: newStatus });
    onRefresh?.();
  }

  async function handleDelete() {
    if (!window.confirm('Delete this task?')) return;
    await api.deleteTask(projectId, task.id);
    onRefresh?.();
  }

  function handleEditClick() {
    dispatch({ type: 'SET_EDITING_TASK', id: task.id });
  }

  function handleEditDone() {
    dispatch({ type: 'SET_EDITING_TASK', id: null });
    onRefresh?.();
  }

  function handleAddSubtask() {
    dispatch({ type: 'TOGGLE_ADD_SUBTASK_FORM', id: task.id });
  }

  function handleSubtaskCreated() {
    dispatch({ type: 'TOGGLE_ADD_SUBTASK_FORM', id: task.id });
    onRefresh?.();
  }

  function handleAddNote() {
    dispatch({ type: 'TOGGLE_ADD_TASK_NOTE_FORM', id: task.id });
  }

  function handleNoteCreated() {
    dispatch({ type: 'TOGGLE_ADD_TASK_NOTE_FORM', id: task.id });
    onRefresh?.();
  }

  if (isEditing) {
    return (
      <div className="task-group" data-testid={`task-item-${task.id}`}>
        <TaskForm
          projectId={projectId}
          task={task}
          onSuccess={handleEditDone}
          onCancel={() => dispatch({ type: 'SET_EDITING_TASK', id: null })}
        />
      </div>
    );
  }

  return (
    <div className="task-group" data-testid={`task-item-${task.id}`}>
      <div className="task-item">
        <div className="task-header" onClick={handleToggle}>
          <button
            className={`task-toggle ${expanded ? 'open' : ''}`}
            onClick={handleToggle}
            type="button"
            aria-label={expanded ? 'Collapse task' : 'Expand task'}
          >
            {expanded ? '\u25BC' : '\u25B6'}
          </button>
          <span className="task-title">{task.title}</span>
          <StatusBadge status={task.status} />
          {task.urgent && <span className="badge badge-urgent">urgent</span>}
        </div>

        {expanded && (
          <div className="task-body">
            {task.description && (
              <div
                className="markdown-body"
                dangerouslySetInnerHTML={{ __html: marked.parse(task.description) }}
              />
            )}

            <StatusDropdown
              currentStatus={task.status}
              onStatusChange={handleStatusChange}
            />

            {hasSubtasks && (
              <TaskList
                tasks={task.subtasks}
                projectId={projectId}
                depth={depth + 1}
                onRefresh={onRefresh}
              />
            )}

            <TaskNoteList taskId={task.id} notes={task.notes ?? null} />

            {showSubtaskForm && (
              <TaskForm
                projectId={projectId}
                task={null}
                parentTaskId={task.id}
                onSuccess={handleSubtaskCreated}
                onCancel={() => dispatch({ type: 'TOGGLE_ADD_SUBTASK_FORM', id: task.id })}
              />
            )}

            {showNoteForm && (
              <TaskNoteForm
                taskId={task.id}
                onSuccess={handleNoteCreated}
                onCancel={() => dispatch({ type: 'TOGGLE_ADD_TASK_NOTE_FORM', id: task.id })}
              />
            )}

            <div className="task-actions">
              <button type="button" className="btn btn-small" onClick={handleEditClick}>
                Edit
              </button>
              <button type="button" className="btn btn-small" onClick={handleAddSubtask}>
                {showSubtaskForm ? 'Cancel Subtask' : 'Add Subtask'}
              </button>
              <button type="button" className="btn btn-small" onClick={handleAddNote}>
                {showNoteForm ? 'Cancel Note' : 'Add Note'}
              </button>
              <button type="button" className="btn btn-small btn-danger" onClick={handleDelete}>
                Delete
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
