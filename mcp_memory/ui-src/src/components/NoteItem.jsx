import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAppState, useAppDispatch } from '../context/AppContext';
import MarkdownBody from './MarkdownBody';
import NoteForm from './NoteForm';
import ConfirmDialog from './ConfirmDialog';
import { formatRelativeTime } from '../utils';
import * as api from '../api';

export default function NoteItem({ note, projectId, projectName, onRefresh }) {
  const { expandedNotes, editingNoteId } = useAppState();
  const dispatch = useAppDispatch();
  const [confirmState, setConfirmState] = useState(null);
  const isExpanded = expandedNotes.has(note.id);
  const isEditing = editingNoteId === note.id;

  function toggleExpand() {
    dispatch({ type: 'TOGGLE_NOTE_EXPANDED', id: note.id });
  }

  function handleDelete() {
    setConfirmState({
      message: `Delete note "${note.title}"?`,
      onConfirm: async () => {
        setConfirmState(null);
        await api.deleteNote(projectId, note.id);
        onRefresh();
      },
    });
  }

  function startEdit() {
    dispatch({ type: 'SET_EDITING_NOTE', id: note.id });
  }

  function cancelEdit() {
    dispatch({ type: 'SET_EDITING_NOTE', id: null });
  }

  return (
    <div className="note-item" data-testid={`note-${note.id}`}>
      {confirmState && (
        <ConfirmDialog
          message={confirmState.message}
          onConfirm={confirmState.onConfirm}
          onCancel={() => setConfirmState(null)}
        />
      )}
      <div className="note-header" onClick={toggleExpand} role="button" tabIndex={0}>
        <button className={`task-toggle${isExpanded ? ' open' : ''}`} type="button">▶</button>
        <span className="note-title">{note.title}</span>
        <span
          className="entity-id-chip"
          title="Copy ID"
          onClick={(e) => {
            e.stopPropagation();
            navigator.clipboard.writeText(note.id);
            e.currentTarget.classList.add('copied');
            setTimeout(() => e.currentTarget.classList.remove('copied'), 1200);
          }}
        >
          <span className="id-text">#{note.id.slice(0, 8)}</span>
        </span>
        <span className="note-date" title={note.created_at ? new Date(note.created_at).toLocaleString() : ''} style={{ fontSize: '10px', color: 'var(--text-dim)', marginLeft: 'auto', marginRight: '10px' }}>
          {formatRelativeTime(note.updated_at || note.created_at)}
        </span>
        <div className="header-actions" onClick={(e) => e.stopPropagation()}>
          <button type="button" className="icon-btn" onClick={startEdit} title="Edit">✎</button>
          <button type="button" className="icon-btn danger" onClick={handleDelete} title="Delete">✗</button>
        </div>
        {note.note_type && (
          <span className={`note-type-pill note-type-${note.note_type}`}>{note.note_type}</span>
        )}
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
            <div className="note-view-content">
              <div className="note-text">
                <MarkdownBody content={note.note_text} />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
