import { useState } from 'react';
import CustomSelect from './CustomSelect';
import * as api from '../api';

const NOTE_TYPES = ['context', 'investigation', 'implementation', 'bug', 'handover'];

export default function TaskNoteForm({ taskId, onSuccess, onCancel }) {
  const [title, setTitle] = useState('');
  const [noteText, setNoteText] = useState('');
  const [noteType, setNoteType] = useState('context');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!title.trim() || !noteText.trim()) return;

    setSubmitting(true);
    setError(null);
    try {
      await api.createTaskNote(taskId, {
        title: title.trim(),
        note_text: noteText.trim(),
        note_type: noteType,
      });
      onSuccess?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="inline-form" onSubmit={handleSubmit} data-testid="task-note-form">
      {error && <div className="form-error">{error}</div>}
      <div className="form-group">
        <label htmlFor="task-note-title">Title</label>
        <input
          id="task-note-title"
          className="form-control"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Note title"
          required
        />
      </div>
      <div className="form-group">
        <label htmlFor="task-note-text">Note</label>
        <textarea
          id="task-note-text"
          className="form-control"
          value={noteText}
          onChange={(e) => setNoteText(e.target.value)}
          placeholder="Note content"
          rows={4}
          required
        />
      </div>
      <div className="form-group">
        <label>Type</label>
        <CustomSelect
          value={noteType}
          onChange={setNoteType}
          options={NOTE_TYPES.map((t) => ({ value: t, label: t }))}
        />
      </div>
      <div className="form-actions">
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? 'Saving...' : 'Add Note'}
        </button>
        <button type="button" className="btn btn-secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
