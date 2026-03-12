import { useNavigate } from 'react-router-dom';
import { entityNavTarget } from '../utils';

const TYPE_LABELS = {
  task: 'Task',
  decision: 'Decision',
  note: 'Note',
  global_note: 'Global Note',
  task_note: 'Task Note',
};

export default function SearchResultItem({ result }) {
  const navigate = useNavigate();
  const target = entityNavTarget(result);

  function handleClick() {
    if (!target) return;
    if (target.projectName) {
      navigate(`/${target.projectName}/${target.tab}`);
    } else {
      navigate('/global');
    }
  }

  const score = result.score != null ? Math.round(result.score * 100) : null;

  return (
    <div
      className="search-result-item"
      onClick={handleClick}
      role="button"
      tabIndex={0}
      data-testid={`search-result-${result.id}`}
    >
      <div className="search-result-header">
        <span className="search-result-type">
          {TYPE_LABELS[result.entity_type] || result.entity_type}
        </span>
        <span className="search-result-title">{result.title}</span>
        {score !== null && (
          <span className="search-result-score">{score}%</span>
        )}
      </div>
      {result.project_name && (
        <span className="search-result-project">{result.project_name}</span>
      )}
      {result.status && (
        <span className={`status-badge status-${result.status}`}>{result.status}</span>
      )}
      {result.note_type && (
        <span className="note-type-pill">{result.note_type}</span>
      )}
    </div>
  );
}
