import { useState } from 'react';
import * as api from '../api';

const NOTE_TYPES = ['foundation', 'implementation', 'context'];

export default function GlobalNoteForm({ onSuccess, onCancel }) {
  const [title, setTitle] = useState('');
  const [noteText, setNoteText] = useState('');
  const [noteType, setNoteType] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!title.trim() || !noteText.trim()) return;

    setSubmitting(true);
    setError(null);
    try {
      await api.createGlobalNote({
        title: title.trim(),
        note_text: noteText.trim(),
        note_type: noteType || null,
      });
      onSuccess();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="inline-form" onSubmit={handleSubmit} data-testid="global-note-form">
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
        {NOTE_TYPES.map((t) => (
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
          {submitting ? 'Saving...' : 'Create'}
        </button>
        <button type="button" className="btn btn-secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
