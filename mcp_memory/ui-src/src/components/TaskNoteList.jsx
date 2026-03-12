import { useState, useEffect } from 'react';
import * as api from '../api';
import TaskNoteForm from './TaskNoteForm';

export default function TaskNoteList({ taskId, notes: notesProp }) {
  const [notes, setNotes] = useState(notesProp ?? null);
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    if (notesProp != null) {
      setNotes(notesProp);
      return;
    }
    if (!taskId) return;
    api.getTaskNotes(taskId).then(setNotes).catch(() => setNotes([]));
  }, [taskId, notesProp]);

  async function refresh() {
    if (!taskId) return;
    const data = await api.getTaskNotes(taskId);
    setNotes(data);
  }

  function handleNoteSuccess() {
    setShowForm(false);
    refresh();
  }

  if (!notes) return null;

  return (
    <div className="task-notes" data-testid="task-note-list">
      <h4>Notes ({notes.length})</h4>
      {notes.length === 0 && <p className="nav-hint">No notes yet.</p>}
      {notes.map((note) => (
        <div key={note.id} className="task-note-item">
          <div className="task-note-header">
            <strong>{note.title}</strong>
            {note.note_type && (
              <span className="note-type-pill">{note.note_type}</span>
            )}
          </div>
          {note.note_text && <p className="task-note-body">{note.note_text}</p>}
        </div>
      ))}
      {showForm ? (
        <TaskNoteForm
          taskId={taskId}
          onSuccess={handleNoteSuccess}
          onCancel={() => setShowForm(false)}
        />
      ) : (
        <button
          type="button"
          className="btn btn-small"
          onClick={() => setShowForm(true)}
        >
          + Add Note
        </button>
      )}
    </div>
  );
}
