import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAppState, useAppDispatch } from '../context/AppContext';
import MarkdownBody from './MarkdownBody';
import { formatRelativeTime } from '../utils';
import * as api from '../api';

const NOTE_TYPES = ['foundation', 'implementation', 'context'];

export default function GlobalNoteItem({ note, onRefresh }) {
  const { expandedGlobalNotes } = useAppState();
  const dispatch = useAppDispatch();
  const isExpanded = expandedGlobalNotes.has(note.id);

  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(note.title);
  const [noteText, setNoteText] = useState(note.note_text);
  const [noteType, setNoteType] = useState(note.note_type ?? '');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  function toggleExpand() {
    dispatch({ type: 'TOGGLE_GLOBAL_NOTE_EXPANDED', id: note.id });
  }

  function startEdit() {
    setTitle(note.title);
    setNoteText(note.note_text);
    setNoteType(note.note_type ?? '');
    setEditing(true);
  }

  function cancelEdit() {
    setEditing(false);
    setError(null);
  }

  async function handleSave(e) {
    e.preventDefault();
    if (!title.trim() || !noteText.trim()) return;

    setSubmitting(true);
    setError(null);
    try {
      await api.updateGlobalNote(note.id, {
        title: title.trim(),
        note_text: noteText.trim(),
        note_type: noteType || null,
      });
      setEditing(false);
      onRefresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!window.confirm(`Delete note "${note.title}"?`)) return;
    await api.deleteGlobalNote(note.id);
    onRefresh();
  }

  return (
    <div className="note-item" data-testid={`global-note-${note.id}`}>
      <div className="note-header" onClick={toggleExpand} role="button" tabIndex={0}>
        <span className="note-title">{note.title}</span>
        {note.note_type && (
          <span className="note-type-pill">{note.note_type}</span>
        )}
        <span className="note-time">
          {formatRelativeTime(note.updated_at || note.created_at)}
        </span>
      </div>

      {isExpanded && (
        <div className="note-body">
          {editing ? (
            <form className="inline-form" onSubmit={handleSave} data-testid="global-note-edit-form">
              {error && <div className="form-error">{error}</div>}
              <input
                type="text"
                className="form-control"
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
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                rows={4}
                required
              />
              <div className="form-actions">
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? 'Saving...' : 'Save'}
                </button>
                <button type="button" className="btn btn-secondary" onClick={cancelEdit}>
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <>
              <MarkdownBody content={note.note_text} />
              <div className="item-actions">
                <Link to={`/global/notes/${note.id}`} className="btn btn-sm">
                  View Detail &rarr;
                </Link>
                <button className="btn btn-sm" onClick={startEdit}>Edit</button>
                <button className="btn btn-sm btn-danger" onClick={handleDelete}>Delete</button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
