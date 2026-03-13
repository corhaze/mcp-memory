import { useState } from 'react';
import { STATUS_OPTIONS } from '../utils';
import CustomSelect from './CustomSelect';
import * as api from '../api';

export default function TaskForm({ projectId, task, parentTaskId, onSuccess, onCancel }) {
  const isEdit = task != null;

  const [title, setTitle] = useState(task?.title ?? '');
  const [description, setDescription] = useState(task?.description ?? '');
  const [status, setStatus] = useState(task?.status ?? 'open');
  const [urgent, setUrgent] = useState(task?.urgent ?? false);
  const [complex, setComplex] = useState(task?.complex ?? false);
  const [blockedBy, setBlockedBy] = useState(task?.blocked_by_task_id ?? '');
  const [nextAction, setNextAction] = useState(task?.next_action ?? '');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!title.trim()) return;

    setSubmitting(true);
    setError(null);

    try {
      if (isEdit) {
        const changed = {};
        if (title.trim() !== (task.title ?? '')) changed.title = title.trim();
        if (description !== (task.description ?? '')) changed.description = description;
        if (status !== (task.status ?? 'open')) changed.status = status;
        if (urgent !== (task.urgent ?? false)) changed.urgent = urgent;
        if (complex !== (task.complex ?? false)) changed.complex = complex;
        const newBlocked = blockedBy.trim() || null;
        if (newBlocked !== (task.blocked_by_task_id ?? null)) changed.blocked_by_task_id = newBlocked;
        if (nextAction !== (task.next_action ?? '')) changed.next_action = nextAction;

        if (Object.keys(changed).length > 0) {
          await api.updateTask(projectId, task.id, changed);
        }
      } else {
        const data = { title: title.trim(), status };
        if (description) data.description = description;
        if (urgent) data.urgent = true;
        if (complex) data.complex = true;
        if (blockedBy.trim()) data.blocked_by_task_id = blockedBy.trim();
        if (nextAction) data.next_action = nextAction;
        if (parentTaskId) data.parent_task_id = parentTaskId;
        await api.createTask(projectId, data);
      }
      onSuccess?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="inline-form" onSubmit={handleSubmit} data-testid="task-form">
      {error && <div className="form-error">{error}</div>}
      <div className="form-group">
        <label htmlFor="task-title">Title</label>
        <input
          id="task-title"
          className="form-control"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Task title"
          required
        />
      </div>
      <div className="form-group">
        <label htmlFor="task-description">Description</label>
        <textarea
          id="task-description"
          className="form-control"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Task description (markdown)"
          rows={4}
        />
      </div>
      <div className="form-group">
        <label>Status</label>
        <CustomSelect
          value={status}
          onChange={setStatus}
          options={STATUS_OPTIONS.map((s) => ({ value: s, label: s }))}
        />
      </div>
      <div className="form-group form-checkbox">
        <label>
          <input
            type="checkbox"
            checked={urgent}
            onChange={(e) => setUrgent(e.target.checked)}
          />
          Urgent
        </label>
      </div>
      <div className="form-group form-checkbox">
        <label>
          <input
            type="checkbox"
            checked={complex}
            onChange={(e) => setComplex(e.target.checked)}
          />
          Complex
        </label>
      </div>
      <div className="form-group">
        <label htmlFor="task-blocked-by">Blocked by (task ID)</label>
        <input
          id="task-blocked-by"
          className="form-control"
          type="text"
          value={blockedBy}
          onChange={(e) => setBlockedBy(e.target.value)}
          placeholder="Task ID"
        />
      </div>
      <div className="form-group">
        <label htmlFor="task-next-action">Next action</label>
        <input
          id="task-next-action"
          className="form-control"
          type="text"
          value={nextAction}
          onChange={(e) => setNextAction(e.target.value)}
          placeholder="Next action"
        />
      </div>
      <div className="form-actions">
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? 'Saving...' : isEdit ? 'Update Task' : 'Create Task'}
        </button>
        <button type="button" className="btn btn-secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
