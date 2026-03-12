import { useAppState, useAppDispatch } from '../context/AppContext';
import NoteItem from './NoteItem';
import NoteForm from './NoteForm';

const FILTERS = ['', 'foundation'];
const FILTER_LABELS = { '': 'All', foundation: 'Foundation' };

export default function NotePanel({ notes, projectId, projectName, onRefresh }) {
  const { noteFilter, showAddNoteForm } = useAppState();
  const dispatch = useAppDispatch();

  const filtered = (notes || []).filter(
    (n) => !noteFilter || n.note_type === noteFilter,
  );

  function toggleAddForm() {
    dispatch({ type: 'SET_SHOW_ADD_NOTE_FORM', value: !showAddNoteForm });
  }

  return (
    <div data-testid="note-panel">
      <div className="panel-toolbar">
        <div className="filter-bar">
          {FILTERS.map((f) => (
            <button
              key={f}
              className={`btn btn-sm ${noteFilter === f ? 'active' : ''}`}
              onClick={() => dispatch({ type: 'SET_NOTE_FILTER', value: f })}
            >
              {FILTER_LABELS[f]}
            </button>
          ))}
        </div>
        <button
          className="btn btn-primary btn-sm"
          onClick={toggleAddForm}
        >
          {showAddNoteForm ? 'Cancel' : 'Add Note'}
        </button>
      </div>

      {showAddNoteForm && (
        <NoteForm
          projectId={projectId}
          note={null}
          onSuccess={() => { dispatch({ type: 'SET_SHOW_ADD_NOTE_FORM', value: false }); onRefresh(); }}
          onCancel={() => dispatch({ type: 'SET_SHOW_ADD_NOTE_FORM', value: false })}
        />
      )}

      {filtered.length === 0 ? (
        <p className="nav-hint">No notes found.</p>
      ) : (
        filtered.map((n) => (
          <NoteItem
            key={n.id}
            note={n}
            projectId={projectId}
            projectName={projectName}
            onRefresh={onRefresh}
          />
        ))
      )}
    </div>
  );
}
