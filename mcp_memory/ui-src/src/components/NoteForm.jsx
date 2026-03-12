import { useState } from 'react';
import * as api from '../api';

const NOTE_TYPES = ['', 'foundation', 'context', 'investigation', 'implementation', 'bug', 'handover'];

export default function NoteForm({ projectId, note, onSuccess, onCancel }) {
  const isEdit = Boolean(note);
  const [title, setTitle] = useState(note?.title ?? '');
  const [noteText, setNoteText] = useState(note?.note_text ?? '');
  const [noteType, setNoteType] = useState(note?.note_type ?? '');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!title.trim() || !noteText.trim()) return;

    setSubmitting(true);
    setError(null);
    try {
      const data = {
        title: title.trim(),
        note_text: noteText.trim(),
        note_type: noteType || null,
      };
      if (isEdit) {
        await api.updateNote(projectId, note.id, data);
      } else {
        await api.createNote(projectId, data);
      }
      onSuccess();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="inline-form" onSubmit={handleSubmit} data-testid="note-form">
      {error && <div className="form-error">{error}</div>}
      <input
        type="text"
        className="form-control"
        placeholder="Note title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        required
      />
      <select
        className="form-control"
        value={noteType}
        onChange={(e) => setNoteType(e.target.value)}
      >
        <option value="">No type</option>
        {NOTE_TYPES.filter(Boolean).map((t) => (
          <option key={t} value={t}>{t}</option>
        ))}
      </select>
      <textarea
        className="form-control"
        placeholder="Note text (markdown)"
        value={noteText}
        onChange={(e) => setNoteText(e.target.value)}
        rows={4}
        required
      />
      <div className="form-actions">
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? 'Saving...' : isEdit ? 'Update' : 'Create'}
        </button>
        <button type="button" className="btn btn-secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
