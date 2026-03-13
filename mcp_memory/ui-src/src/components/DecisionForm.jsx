import { useState } from 'react';
import CustomSelect from './CustomSelect';
import * as api from '../api';

const DECISION_STATUS_OPTIONS = [
  { value: 'active', label: 'active', className: 'badge-active' },
  { value: 'draft', label: 'draft', className: 'badge-draft' },
  { value: 'superseded', label: 'superseded', className: 'badge-superseded' },
];

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
      <div className="form-group">
        <label htmlFor="decision-title">Title</label>
        <input
          id="decision-title"
          type="text"
          className="form-control"
          placeholder="Decision title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
      </div>
      <div className="form-group">
        <label>Status</label>
        <CustomSelect
          value={status}
          onChange={setStatus}
          options={DECISION_STATUS_OPTIONS}
        />
      </div>
      <div className="form-group">
        <label htmlFor="decision-text">Decision text</label>
        <textarea
          id="decision-text"
          className="form-control"
          placeholder="Decision text (markdown)"
          value={decisionText}
          onChange={(e) => setDecisionText(e.target.value)}
          rows={3}
        />
      </div>
      <div className="form-group">
        <label htmlFor="decision-rationale">Rationale</label>
        <textarea
          id="decision-rationale"
          className="form-control"
          placeholder="Rationale"
          value={rationale}
          onChange={(e) => setRationale(e.target.value)}
          rows={2}
        />
      </div>
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
