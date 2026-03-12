import { useParams, Link, useNavigate } from 'react-router-dom';
import { marked } from 'marked';
import { useTask } from '../hooks/useTask';
import { useProjects } from '../hooks/useProjects';
import { useAppState, useAppDispatch } from '../context/AppContext';
import StatusBadge from './StatusBadge';
import StatusDropdown from './StatusDropdown';
import TaskForm from './TaskForm';
import TaskNoteList from './TaskNoteList';
import * as api from '../api';

export default function TaskDetail() {
  const { projectName, taskId } = useParams();
  const navigate = useNavigate();
  const { projects } = useProjects();
  const state = useAppState();
  const dispatch = useAppDispatch();

  const project = projects?.find((p) => p.name === projectName) ?? null;
  const { task, loading, error, refresh } = useTask(project?.id, taskId);
  const isEditing = state.editingTaskId === taskId;

  async function handleStatusChange(newStatus) {
    if (!project) return;
    await api.updateTask(project.id, taskId, { status: newStatus });
    refresh();
  }

  async function handleDelete() {
    if (!project) return;
    if (!window.confirm('Delete this task?')) return;
    await api.deleteTask(project.id, taskId);
    navigate(`/${projectName}/tasks`);
  }

  function handleEditToggle() {
    dispatch({ type: 'SET_EDITING_TASK', id: isEditing ? null : taskId });
  }

  function handleEditSuccess() {
    dispatch({ type: 'SET_EDITING_TASK', id: null });
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
    <div data-testid="task-detail">
      <Link to={`/${projectName}/tasks`} className="back-link">&larr; Back to tasks</Link>

      <header className="task-detail-header">
        <div className="project-title-row">
          <h2>{task.title}</h2>
          <StatusBadge status={task.status} />
          {task.urgent && <span className="badge badge-urgent">urgent</span>}
          <button
            type="button"
            className="btn btn-small"
            onClick={handleEditToggle}
          >
            {isEditing ? 'Cancel Edit' : 'Edit'}
          </button>
          <button
            type="button"
            className="btn btn-small btn-danger"
            onClick={handleDelete}
          >
            Delete
          </button>
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
        <div className="task-detail-content">
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

          {task.parent_task_id && (
            <p>
              Parent: <Link to={`/${projectName}/tasks/${task.parent_task_id}`}>
                {task.parent_task_id}
              </Link>
            </p>
          )}

          {task.blocked_by_task_id && (
            <p>
              Blocked by: <Link to={`/${projectName}/tasks/${task.blocked_by_task_id}`}>
                {task.blocked_by_task_id}
              </Link>
            </p>
          )}

          {task.subtasks && task.subtasks.length > 0 && (
            <div className="subtask-list">
              <h3>Subtasks</h3>
              <ul>
                {task.subtasks.map((sub) => (
                  <li key={sub.id}>
                    <Link to={`/${projectName}/tasks/${sub.id}`}>
                      <StatusBadge status={sub.status} /> {sub.title}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <TaskNoteList taskId={task.id} notes={task.notes ?? null} />

          {task.events && task.events.length > 0 && (
            <div className="event-timeline">
              <h3>Events</h3>
              <ul>
                {task.events.map((evt, i) => (
                  <li key={evt.id ?? i}>
                    <span className="event-type">{evt.event_type}</span>
                    {evt.detail && <span className="event-detail"> — {evt.detail}</span>}
                    {evt.created_at && (
                      <span className="event-time"> ({evt.created_at})</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
