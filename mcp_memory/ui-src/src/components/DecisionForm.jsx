import { useState } from 'react';
import * as api from '../api';

const STATUS_OPTIONS = ['active', 'draft', 'superseded'];

export default function DecisionForm({ projectId, decision, onSuccess, onCancel }) {
  const isEdit = Boolean(decision);
  const [title, setTitle] = useState(decision?.title ?? '');
  const [status, setStatus] = useState(decision?.status ?? 'active');
  const [decisionText, setDecisionText] = useState(decision?.decision_text ?? '');
  const [rationale, setRationale] = useState(decision?.rationale ?? '');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!title.trim()) return;

    setSubmitting(true);
    setError(null);
    try {
      const data = {
        title: title.trim(),
        status,
        decision_text: decisionText.trim(),
        rationale: rationale.trim(),
      };
      if (isEdit) {
        await api.updateDecision(projectId, decision.id, data);
      } else {
        await api.createDecision(projectId, data);
      }
      onSuccess();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="inline-form" onSubmit={handleSubmit} data-testid="decision-form">
      {error && <div className="form-error">{error}</div>}
      <input
        type="text"
        className="form-control"
        placeholder="Decision title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        required
      />
      <select
        className="form-control"
        value={status}
        onChange={(e) => setStatus(e.target.value)}
      >
        {STATUS_OPTIONS.map((s) => (
          <option key={s} value={s}>{s}</option>
        ))}
      </select>
      <textarea
        className="form-control"
        placeholder="Decision text (markdown)"
        value={decisionText}
        onChange={(e) => setDecisionText(e.target.value)}
        rows={3}
      />
      <textarea
        className="form-control"
        placeholder="Rationale"
        value={rationale}
        onChange={(e) => setRationale(e.target.value)}
        rows={2}
      />
      <div className="form-actions">
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? 'Saving...' : isEdit ? 'Update' : 'Create'}
        </button>
        <button type="button" className="btn btn-secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
