import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import MarkdownBody from './MarkdownBody';
import { useProjects } from '../hooks/useProjects';
import * as api from '../api';

export default function DecisionDetail() {
  const { projectName, decisionId } = useParams();
  const navigate = useNavigate();
  const { projects } = useProjects();
  const project = projects?.find((p) => p.name === projectName) ?? null;

  const [decision, setDecision] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!project) return;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await api.getProjectDecisions(project.id);
        const items = data.items ?? data;
        const found = items.find((d) => d.id === decisionId);
        if (!found) throw new Error('Decision not found');
        if (!cancelled) setDecision(found);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [project, decisionId]);

  const backLink = `/${projectName}/decisions`;

  if (loading) {
    return <div className="panel"><p className="nav-hint">Loading decision...</p></div>;
  }

  if (error) {
    return (
      <div className="panel">
        <Link to={backLink}>&larr; Back to Decisions</Link>
        <p className="nav-hint">Error: {error}</p>
      </div>
    );
  }

  if (!decision) {
    return (
      <div className="panel">
        <Link to={backLink}>&larr; Back to Decisions</Link>
        <p className="nav-hint">Decision not found.</p>
      </div>
    );
  }

  return (
    <div className="panel task-detail-container" data-testid="decision-detail">
      <div className="task-detail-nav">
        <button
          type="button"
          className="task-detail-back btn-secondary"
          onClick={() => navigate(backLink)}
        >
          &larr; Back to Decisions
        </button>
      </div>

      <header className="task-detail-header">
        <div className="task-detail-title-row">
          <h2 className="task-detail-title">{decision.title}</h2>
          <span className={`status-badge badge-${decision.status}`}>{decision.status}</span>
        </div>
      </header>

      {decision.decision_text && (
        <div className="task-detail-section">
          <h3>Decision</h3>
          <MarkdownBody content={decision.decision_text} />
        </div>
      )}

      {decision.rationale && (
        <div className="task-detail-section">
          <h3>Rationale</h3>
          <div className="markdown-body">{decision.rationale}</div>
        </div>
      )}
    </div>
  );
}
