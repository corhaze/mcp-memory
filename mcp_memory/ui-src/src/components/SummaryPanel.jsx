import { useState } from 'react';
import MarkdownBody from './MarkdownBody';
import * as api from '../api';

export default function SummaryPanel({ summary, projectId, onRefresh }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState('');
  const [saving, setSaving] = useState(false);

  const summaryText = typeof summary === 'string' ? summary : summary?.text ?? '';

  function startEdit() {
    setText(summaryText);
    setEditing(true);
  }

  async function handleSave() {
    setSaving(true);
    try {
      await api.updateProjectSummary(projectId, text);
      setEditing(false);
      onRefresh();
    } catch {
      // keep editing on error
    } finally {
      setSaving(false);
    }
  }

  if (editing) {
    return (
      <div data-testid="summary-panel">
        <textarea
          className="form-control"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={10}
          data-testid="summary-textarea"
        />
        <div className="form-actions">
          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
          <button
            className="btn btn-secondary"
            onClick={() => setEditing(false)}
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="summary-panel">
      <div className="summary-toolbar">
        <button className="filter-btn" onClick={startEdit}>✎ EDIT</button>
      </div>
      {summaryText ? (
        <div className="project-summary">
          <MarkdownBody content={summaryText} />
        </div>
      ) : (
        <p className="nav-hint">No summary yet.</p>
      )}
    </div>
  );
}
