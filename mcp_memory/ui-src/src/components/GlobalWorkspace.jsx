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
      <header id="project-header" className="global-workspace-header">
        <div className="project-title-row">
          <h2>Global Workspace</h2>
          <span className="global-workspace-badge">cross-project</span>
        </div>
        <p className="project-description global-workspace-description">
          Shared standards, architecture decisions, and context for all projects.
        </p>
      </header>

      <TabBar tabs={TABS} activeTab="notes" onTabClick={() => {}} />

      <section className="panel" data-testid="panel-notes">
        <div className="panel-toolbar">
          <div className="filter-group">
            {FILTERS.map((f) => (
              <button
                key={f}
                type="button"
                className={`filter-btn${globalNoteFilter === f ? ' active' : ''}`}
                onClick={() => dispatch({ type: 'SET_GLOBAL_NOTE_FILTER', value: f })}
              >
                {FILTER_LABELS[f]}
              </button>
            ))}
          </div>
          <button type="button" className="filter-btn" onClick={toggleAddForm}>
            {showAddGlobalNoteForm ? 'Cancel' : '+ Add Note'}
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
