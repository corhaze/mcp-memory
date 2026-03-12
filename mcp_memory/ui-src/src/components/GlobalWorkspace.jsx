import { useAppState, useAppDispatch } from '../context/AppContext';
import { useGlobalNotes } from '../hooks/useGlobalNotes';
import TabBar from './TabBar';
import GlobalNoteItem from './GlobalNoteItem';
import GlobalNoteForm from './GlobalNoteForm';

const TABS = [{ name: 'notes', label: 'Notes' }];
const FILTERS = ['', 'foundation'];
const FILTER_LABELS = { '': 'All', foundation: 'Foundation' };

export default function GlobalWorkspace() {
  const { globalNoteFilter, showAddGlobalNoteForm } = useAppState();
  const dispatch = useAppDispatch();
  const { globalNotes, loading, error, refresh } = useGlobalNotes();

  const filtered = (globalNotes || []).filter(
    (n) => !globalNoteFilter || n.note_type === globalNoteFilter,
  );

  function toggleAddForm() {
    dispatch({ type: 'SET_SHOW_ADD_GLOBAL_NOTE_FORM', value: !showAddGlobalNoteForm });
  }

  return (
    <div data-testid="global-workspace">
      <header id="project-header">
        <div className="project-title-row">
          <h2>Global Workspace</h2>
        </div>
      </header>

      <TabBar tabs={TABS} activeTab="notes" onTabClick={() => {}} />

      <section className="panel" data-testid="panel-notes">
        <div className="panel-toolbar">
          <div className="filter-bar">
            {FILTERS.map((f) => (
              <button
                key={f}
                className={`btn btn-sm ${globalNoteFilter === f ? 'active' : ''}`}
                onClick={() => dispatch({ type: 'SET_GLOBAL_NOTE_FILTER', value: f })}
              >
                {FILTER_LABELS[f]}
              </button>
            ))}
          </div>
          <button className="btn btn-primary btn-sm" onClick={toggleAddForm}>
            {showAddGlobalNoteForm ? 'Cancel' : 'Add Note'}
          </button>
        </div>

        {showAddGlobalNoteForm && (
          <GlobalNoteForm
            onSuccess={() => {
              dispatch({ type: 'SET_SHOW_ADD_GLOBAL_NOTE_FORM', value: false });
              refresh();
            }}
            onCancel={() => dispatch({ type: 'SET_SHOW_ADD_GLOBAL_NOTE_FORM', value: false })}
          />
        )}

        {loading ? (
          <p className="nav-hint">Loading...</p>
        ) : error ? (
          <p className="nav-hint">Error: {error}</p>
        ) : filtered.length === 0 ? (
          <p className="nav-hint">No global notes found.</p>
        ) : (
          filtered.map((n) => (
            <GlobalNoteItem key={n.id} note={n} onRefresh={refresh} />
          ))
        )}
      </section>
    </div>
  );
}
