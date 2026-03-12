import { Link } from 'react-router-dom';
import { useAppState, useAppDispatch } from '../context/AppContext';
import MarkdownBody from './MarkdownBody';
import NoteForm from './NoteForm';
import { formatRelativeTime } from '../utils';
import * as api from '../api';

export default function NoteItem({ note, projectId, projectName, onRefresh }) {
  const { expandedNotes, editingNoteId } = useAppState();
  const dispatch = useAppDispatch();
  const isExpanded = expandedNotes.has(note.id);
  const isEditing = editingNoteId === note.id;

  function toggleExpand() {
    dispatch({ type: 'TOGGLE_NOTE_EXPANDED', id: note.id });
  }

  async function handleDelete() {
    if (!window.confirm(`Delete note "${note.title}"?`)) return;
    await api.deleteNote(projectId, note.id);
    onRefresh();
  }

  function startEdit() {
    dispatch({ type: 'SET_EDITING_NOTE', id: note.id });
  }

  function cancelEdit() {
    dispatch({ type: 'SET_EDITING_NOTE', id: null });
  }

  return (
    <div className="note-item" data-testid={`note-${note.id}`}>
      <div className="note-header" onClick={toggleExpand} role="button" tabIndex={0}>
        <span className="note-title">{note.title}</span>
        {note.note_type && (
          <span className="note-type-pill">{note.note_type}</span>
        )}
        <span className="note-time">{formatRelativeTime(note.updated_at || note.created_at)}</span>
      </div>

      {isExpanded && (
        <div className="note-body">
          {isEditing ? (
            <NoteForm
              projectId={projectId}
              note={note}
              onSuccess={() => { cancelEdit(); onRefresh(); }}
              onCancel={cancelEdit}
            />
          ) : (
            <>
              <MarkdownBody content={note.note_text} />
              <div className="item-actions">
                <Link to={`/${projectName}/notes/${note.id}`} className="btn btn-sm">
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
