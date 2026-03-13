import { useState } from 'react';
import MarkdownBody from './MarkdownBody';
import DecisionForm from './DecisionForm';
import ConfirmDialog from './ConfirmDialog';
import { formatRelativeTime } from '../utils';
import * as api from '../api';

export default function DecisionItem({ decision, projectId, onRefresh }) {
  const [editing, setEditing] = useState(false);
  const [confirmState, setConfirmState] = useState(null);

  function handleDelete() {
    setConfirmState({
      message: `Delete decision "${decision.title}"?`,
      onConfirm: async () => {
        setConfirmState(null);
        await api.deleteDecision(projectId, decision.id);
        onRefresh();
      },
    });
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
    <div className={`decision-item${decision.status === 'superseded' ? ' superseded' : ''}`} data-testid={`decision-${decision.id}`}>
      {confirmState && (
        <ConfirmDialog
          message={confirmState.message}
          onConfirm={confirmState.onConfirm}
          onCancel={() => setConfirmState(null)}
        />
      )}
      <div className="decision-header">
        <span className="decision-title">{decision.title}</span>
        <span
          className="entity-id-chip"
          title="Copy ID"
          onClick={(e) => {
            navigator.clipboard.writeText(decision.id);
            e.currentTarget.classList.add('copied');
            setTimeout(() => e.currentTarget.classList.remove('copied'), 1200);
          }}
        >
          <span className="id-text">#{decision.id.slice(0, 8)}</span>
        </span>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span className="decision-date" title={decision.created_at ? new Date(decision.created_at).toLocaleString() : ''} style={{ fontSize: '10px', color: 'var(--text-dim)' }}>
            {formatRelativeTime(decision.created_at)}
          </span>
          <span className={`status-badge badge-${decision.status}`}>{decision.status}</span>
        </div>
        <div className="header-actions">
          <button type="button" className="icon-btn" onClick={() => setEditing(true)} title="Edit">✎</button>
          <button type="button" className="icon-btn danger" onClick={handleDelete} title="Delete">✗</button>
        </div>
      </div>
      {decision.decision_text && (
        <div className="decision-text">
          <MarkdownBody content={decision.decision_text} />
        </div>
      )}
      {decision.rationale && (
        <div className="decision-rationale">{decision.rationale}</div>
      )}
      {decision.supersedes_decision_id && (
        <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '6px' }}>
          ↳ Supersedes {decision.supersedes_decision_id.slice(0, 8)}
        </div>
      )}
    </div>
  );
}
