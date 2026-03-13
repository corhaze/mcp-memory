import { useState } from 'react';
import { marked } from 'marked';
import { Link } from 'react-router-dom';
import { useAppState, useAppDispatch } from '../context/AppContext';
import StatusDropdown from './StatusDropdown';
import TaskForm from './TaskForm';
import TaskNoteList from './TaskNoteList';
import TaskNoteForm from './TaskNoteForm';
import TaskList from './TaskList';
import ConfirmDialog from './ConfirmDialog';
import { statusEmoji, formatRelativeTime } from '../utils';
import * as api from '../api';

function subtaskSummary(task) {
  if (!task.subtasks || task.subtasks.length === 0) return null;
  const total = task.subtasks.length;
  const done = task.subtasks.filter((st) => st.status === 'done').length;
  return <span className="subtask-summary">{done}/{total} completed</span>;
}

export default function TaskItem({ task, projectId, projectName, depth = 0, onRefresh }) {
  const state = useAppState();
  const dispatch = useAppDispatch();
  const [confirmState, setConfirmState] = useState(null);

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

  function handleDelete() {
    setConfirmState({
      message: 'Delete this task?',
      onConfirm: async () => {
        setConfirmState(null);
        await api.deleteTask(projectId, task.id);
        onRefresh?.();
      },
    });
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
    <div className="task-group" data-depth={depth} data-testid={`task-item-${task.id}`}>
      {confirmState && (
        <ConfirmDialog
          message={confirmState.message}
          onConfirm={confirmState.onConfirm}
          onCancel={() => setConfirmState(null)}
        />
      )}
      <div className={`task-item ${task.status}`}>
        <div className="task-header">
          {task.urgent && <span className="urgent-dot" title="Urgent" />}
          <div className="task-title-area">
            <div className="task-title">
              {statusEmoji(task.status)}{' '}
              {projectName ? (
                <Link
                  className="task-title-link"
                  to={`/${projectName}/tasks/${task.id}`}
                >
                  {task.title}
                </Link>
              ) : (
                <span className="task-title-link">{task.title}</span>
              )}
            </div>
            <div className="task-meta">
              <span
                className="entity-id-chip"
                title="Copy ID"
                onClick={(e) => {
                  e.stopPropagation();
                  navigator.clipboard.writeText(task.id);
                  e.currentTarget.classList.add('copied');
                  setTimeout(() => e.currentTarget.classList.remove('copied'), 1200);
                }}
              >
                <span className="id-text">#{task.id.slice(0, 8)}</span>
              </span>
              {task.complex && <span className="complex-badge" title="Complex Task">COMPLEX</span>}
              {subtaskSummary(task)}
              {task.blocked_by_task_id && (
                <span className="blocked-by-badge" title={`Blocked by: ${task.blocked_by_task_id}`}>depends on</span>
              )}
              {task.assigned_agent && (
                <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>[{task.assigned_agent}]</span>
              )}
              {depth === 0 && task.created_at && (
                <span
                  className="task-date"
                  title={new Date(task.created_at).toLocaleString()}
                  style={{ fontSize: '10px', color: 'var(--text-dim)', marginLeft: 'auto' }}
                >
                  {formatRelativeTime(task.created_at)}
                </span>
              )}
            </div>
            {task.next_action && (
              <div className="task-next-action">{task.next_action}</div>
            )}
          </div>
          <div className="header-actions">
            <StatusDropdown
              currentStatus={task.status}
              onStatusChange={handleStatusChange}
            />
            <button type="button" className="icon-btn edit-task" onClick={handleEditClick} title="Edit">✎</button>
            <button type="button" className="icon-btn danger delete-task" onClick={handleDelete} title="Delete">✗</button>
          </div>
          <span
            className={`task-toggle${expanded ? ' open' : ''}`}
            onClick={handleToggle}
            role="button"
            tabIndex={0}
            title="Expand"
          >
            ›
          </span>
        </div>

        {expanded && (
          <div className="task-body">
            {task.description && (
              <div
                className="task-description markdown-body"
                dangerouslySetInnerHTML={{ __html: marked.parse(task.description) }}
              />
            )}

            <div className="task-notes-section">
              <div className="task-notes-header">
                <span className="task-notes-label">Notes</span>
                <button type="button" className="add-task-note-btn" onClick={handleAddNote}>
                  {showNoteForm ? '− cancel' : '+ add note'}
                </button>
              </div>
              <TaskNoteList taskId={task.id} notes={task.notes ?? null} />
              {showNoteForm && (
                <TaskNoteForm
                  taskId={task.id}
                  onSuccess={handleNoteCreated}
                  onCancel={() => dispatch({ type: 'TOGGLE_ADD_TASK_NOTE_FORM', id: task.id })}
                />
              )}
            </div>

            {hasSubtasks && (
              <TaskList
                tasks={task.subtasks}
                projectId={projectId}
                projectName={projectName}
                depth={depth + 1}
                onRefresh={onRefresh}
              />
            )}

            <div className="add-subtask-section">
              <button type="button" className="add-subtask-btn" onClick={handleAddSubtask}>
                {showSubtaskForm ? '− Cancel subtask' : '+ Add subtask'}
              </button>
              {showSubtaskForm && (
                <TaskForm
                  projectId={projectId}
                  task={null}
                  parentTaskId={task.id}
                  onSuccess={handleSubtaskCreated}
                  onCancel={() => dispatch({ type: 'TOGGLE_ADD_SUBTASK_FORM', id: task.id })}
                />
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
