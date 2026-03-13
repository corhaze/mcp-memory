import { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { marked } from 'marked';
import { useTask } from '../hooks/useTask';
import { useProjects } from '../hooks/useProjects';
import { useAppState, useAppDispatch } from '../context/AppContext';
import StatusBadge from './StatusBadge';
import StatusDropdown from './StatusDropdown';
import TaskForm from './TaskForm';
import TaskNoteList from './TaskNoteList';
import TaskNoteForm from './TaskNoteForm';
import ConfirmDialog from './ConfirmDialog';
import { formatRelativeTime } from '../utils';
import * as api from '../api';

export default function TaskDetail() {
  const { projectName, taskId } = useParams();
  const navigate = useNavigate();
  const { projects } = useProjects();
  const state = useAppState();
  const dispatch = useAppDispatch();
  const [confirmState, setConfirmState] = useState(null);
  const [expandedSubtasks, setExpandedSubtasks] = useState(new Set());

  function toggleExpand(id) {
    setExpandedSubtasks((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  const project = projects?.find((p) => p.name === projectName) ?? null;
  const { task, loading, error, refresh } = useTask(project?.id, taskId);
  const isEditing = state.editingTaskId === taskId;
  const showNoteForm = state.showAddTaskNoteForm?.has(taskId);

  async function handleStatusChange(newStatus) {
    if (!project) return;
    await api.updateTask(project.id, taskId, { status: newStatus });
    refresh();
  }

  function handleDelete() {
    if (!project) return;
    setConfirmState({
      message: 'Delete this task?',
      onConfirm: async () => {
        setConfirmState(null);
        await api.deleteTask(project.id, taskId);
        navigate(`/${projectName}/tasks`);
      },
    });
  }

  function handleEditToggle() {
    dispatch({ type: 'SET_EDITING_TASK', id: isEditing ? null : taskId });
  }

  function handleEditSuccess() {
    dispatch({ type: 'SET_EDITING_TASK', id: null });
    refresh();
  }

  function handleToggleNoteForm() {
    dispatch({ type: 'TOGGLE_ADD_TASK_NOTE_FORM', id: taskId });
  }

  function handleNoteCreated() {
    dispatch({ type: 'TOGGLE_ADD_TASK_NOTE_FORM', id: taskId });
    refresh();
  }

  if (loading) {
    return <div className="empty-state"><p className="nav-hint">Loading task...</p></div>;
  }

  if (error) {
    return <div className="empty-state"><p className="nav-hint">Error: {error}</p></div>;
  }

  if (!task) {
    return <div className="empty-state"><p className="nav-hint">Task not found.</p></div>;
  }

  return (
    <div className="panel task-detail-container" data-testid="task-detail">
      <div className="task-detail-nav">
        <Link to={`/${projectName}/tasks`} className="task-detail-back btn-secondary">&larr; Back to Tasks</Link>
        {task.parent_task_id && (
          <span className="task-detail-parent">
            &nbsp;·&nbsp;
            <Link to={`/${projectName}/tasks/${task.parent_task_id}`} className="task-detail-parent-link">
              parent: {task.parent_task_id.slice(0, 8)}
            </Link>
          </span>
        )}
      </div>

      <header className="task-detail-header">
        <div className="task-detail-title-row">
          <h2 className="task-detail-title">{task.title}</h2>
          <div className="header-actions">
            <button type="button" className="icon-btn" onClick={handleEditToggle} title="Edit">✎</button>
            <button type="button" className="icon-btn danger" onClick={handleDelete} title="Delete">✗</button>
          </div>
        </div>
        <div className="task-detail-meta">
          <StatusDropdown currentStatus={task.status} onStatusChange={handleStatusChange} align="left" />
          {task.urgent && <span className="status-badge" style={{ color: 'var(--red)', borderColor: 'var(--red)' }}>URGENT</span>}
          <span className="entity-id-chip" title="Copy ID" onClick={(e) => {
            navigator.clipboard.writeText(task.id);
            e.currentTarget.classList.add('copied');
            setTimeout(() => e.currentTarget.classList.remove('copied'), 1200);
          }}>
            <span className="id-text">#{task.id.slice(0, 8)}</span>
          </span>
        </div>
      </header>

      {isEditing && project ? (
        <TaskForm
          projectId={project.id}
          task={task}
          onSuccess={handleEditSuccess}
          onCancel={() => dispatch({ type: 'SET_EDITING_TASK', id: null })}
        />
      ) : (
        <>
          {task.description && (
            <div
              className="task-detail-description markdown-body"
              dangerouslySetInnerHTML={{ __html: marked.parse(task.description) }}
            />
          )}

          {task.next_action && (
            <div className="task-detail-next-action">
              {task.next_action}
            </div>
          )}

          {task.blocked_by_task_id && (
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '1rem' }}>
              <span className="blocked-by-badge">depends on</span>{' '}
              <Link to={`/${projectName}/tasks/${task.blocked_by_task_id}`}>
                {task.blocked_by_task_id.slice(0, 8)}
              </Link>
            </p>
          )}

          {task.subtasks && task.subtasks.length > 0 && (
            <div className="task-detail-section">
              <h3>Subtasks</h3>
              <ul className="task-detail-subtask-list">
                {task.subtasks.map((sub) => (
                  <li key={sub.id} className="task-detail-subtask">
                    <div className="task-detail-subtask-row">
                      <button
                        type="button"
                        className={`subtask-expand-toggle${expandedSubtasks.has(sub.id) ? ' open' : ''}`}
                        onClick={() => toggleExpand(sub.id)}
                      >›</button>
                      <StatusBadge status={sub.status} />
                      <Link to={`/${projectName}/tasks/${sub.id}`} className="task-detail-subtask-title">
                        {sub.title}
                      </Link>
                      <button
                        type="button"
                        className="icon-btn danger"
                        style={{ marginLeft: 'auto', width: '20px', height: '20px', fontSize: '12px' }}
                        onClick={(e) => {
                          e.preventDefault();
                          if (!project) return;
                          setConfirmState({
                            message: `Delete subtask "${sub.title}"?`,
                            onConfirm: async () => {
                              setConfirmState(null);
                              await api.deleteTask(project.id, sub.id);
                              refresh();
                            },
                          });
                        }}
                        title="Delete subtask"
                      >✗</button>
                    </div>
                    {expandedSubtasks.has(sub.id) && (sub.description || sub.next_action) && (
                      <div className="subtask-expand-body">
                        {sub.description && (
                          <div
                            className="subtask-expand-description markdown-body"
                            dangerouslySetInnerHTML={{ __html: marked.parse(sub.description) }}
                          />
                        )}
                        {sub.next_action && (
                          <div className="task-detail-next-action">{sub.next_action}</div>
                        )}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="task-detail-section">
            <h3>Notes ({(task.notes ?? []).length})</h3>
            <TaskNoteList taskId={task.id} notes={task.notes ?? null} bare />
            <button
              type="button"
              className="add-task-note-btn"
              onClick={handleToggleNoteForm}
              style={{ marginTop: '8px' }}
            >
              {showNoteForm ? '− cancel' : '+ add note'}
            </button>
            {showNoteForm && (
              <TaskNoteForm
                taskId={task.id}
                onSuccess={handleNoteCreated}
                onCancel={() => dispatch({ type: 'TOGGLE_ADD_TASK_NOTE_FORM', id: taskId })}
              />
            )}
          </div>

          {task.events && task.events.length > 0 && (
            <div className="task-detail-section">
              <h3>Events</h3>
              <ul className="task-detail-events-list">
                {task.events.map((evt, i) => (
                  <li key={evt.id ?? i} className="task-detail-event">
                    <span className="task-detail-event-type">{evt.event_type}</span>
                    <span className="task-detail-event-note">{evt.detail || ''}</span>
                    {evt.created_at && (
                      <span className="task-detail-event-time">{formatRelativeTime(evt.created_at)}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
      {confirmState && (
        <ConfirmDialog
          message={confirmState.message}
          onConfirm={confirmState.onConfirm}
          onCancel={() => setConfirmState(null)}
        />
      )}
    </div>
  );
}
