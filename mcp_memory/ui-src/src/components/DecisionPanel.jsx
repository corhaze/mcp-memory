import { useState } from 'react';
import { useAppState, useAppDispatch } from '../context/AppContext';
import DecisionItem from './DecisionItem';
import DecisionForm from './DecisionForm';

const FILTERS = ['', 'active', 'draft', 'superseded'];
const FILTER_LABELS = { '': 'All', active: 'Active', draft: 'Draft', superseded: 'Superseded' };

export default function DecisionPanel({ decisions, projectId, onRefresh }) {
  const { decisionFilter } = useAppState();
  const dispatch = useAppDispatch();
  const [showForm, setShowForm] = useState(false);

  const filtered = (decisions || []).filter(
    (d) => !decisionFilter || d.status === decisionFilter,
  );

  return (
    <div data-testid="decision-panel">
      <div className="panel-toolbar">
        <div className="filter-group">
          {FILTERS.map((f) => (
            <button
              key={f}
              type="button"
              className={`filter-btn${decisionFilter === f ? ' active' : ''}`}
              onClick={() => dispatch({ type: 'SET_DECISION_FILTER', value: f })}
            >
              {FILTER_LABELS[f]}
            </button>
          ))}
        </div>
        <button
          type="button"
          className="filter-btn"
          onClick={() => setShowForm((v) => !v)}
        >
          {showForm ? 'Cancel' : '+ Add Decision'}
        </button>
      </div>

      {showForm && (
        <DecisionForm
          projectId={projectId}
          decision={null}
          onSuccess={() => { setShowForm(false); onRefresh(); }}
          onCancel={() => setShowForm(false)}
        />
      )}

      {filtered.length === 0 ? (
        <p className="nav-hint">No decisions found.</p>
      ) : (
        filtered.map((d) => (
          <DecisionItem
            key={d.id}
            decision={d}
            projectId={projectId}
            onRefresh={onRefresh}
          />
        ))
      )}
    </div>
  );
}
