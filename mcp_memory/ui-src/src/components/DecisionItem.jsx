import { useState } from 'react';
import StatusBadge from './StatusBadge';
import MarkdownBody from './MarkdownBody';
import DecisionForm from './DecisionForm';
import * as api from '../api';

export default function DecisionItem({ decision, projectId, onRefresh }) {
  const [editing, setEditing] = useState(false);

  async function handleDelete() {
    if (!window.confirm(`Delete decision "${decision.title}"?`)) return;
    await api.deleteDecision(projectId, decision.id);
    onRefresh();
  }

  if (editing) {
    return (
      <div className="decision-item" data-testid={`decision-${decision.id}`}>
        <DecisionForm
          projectId={projectId}
          decision={decision}
          onSuccess={() => { setEditing(false); onRefresh(); }}
          onCancel={() => setEditing(false)}
        />
      </div>
    );
  }

  return (
    <div className="decision-item" data-testid={`decision-${decision.id}`}>
      <div className="decision-header">
        <span className="decision-title">{decision.title}</span>
        <StatusBadge status={decision.status} />
      </div>
      {decision.decision_text && (
        <MarkdownBody content={decision.decision_text} />
      )}
      {decision.rationale && (
        <div className="decision-rationale">
          <strong>Rationale:</strong> {decision.rationale}
        </div>
      )}
      {decision.superseded_by && (
        <div className="decision-superseded">
          Superseded by: {decision.superseded_by}
        </div>
      )}
      <div className="item-actions">
        <button className="btn btn-sm" onClick={() => setEditing(true)}>Edit</button>
        <button className="btn btn-sm btn-danger" onClick={handleDelete}>Delete</button>
      </div>
    </div>
  );
}
