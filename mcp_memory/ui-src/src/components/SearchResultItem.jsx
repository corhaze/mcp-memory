import { useNavigate } from 'react-router-dom';
import { entityNavTarget } from '../utils';

export default function SearchResultItem({ result }) {
  const navigate = useNavigate();
  const target = entityNavTarget(result);

  function handleClick() {
    if (!target) return;
    navigate(target);
  }

  const score = result.score != null ? Math.round(result.score * 100) + '%' : null;
  const clickableClass = target ? ' search-result-item--clickable' : '';

  return (
    <li
      className={`search-result-item${clickableClass}`}
      onClick={handleClick}
      data-entity-id={result.id}
      data-entity-type={result.entity_type}
      data-project-name={result.project_name || ''}
      data-testid={`search-result-${result.id}`}
    >
      <span className={`entity-type-badge badge-${result.entity_type}`}>
        {result.entity_type}
      </span>
      {result.project_name && (
        <span className="search-result-project">{result.project_name}</span>
      )}
      <span className="search-result-title">{result.title}</span>
      {result.status && (
        <span className={`status-badge badge-${result.status}`}>{result.status}</span>
      )}
      {result.note_type && (
        <span className="note-type-pill">{result.note_type}</span>
      )}
      {score !== null && (
        <span className="search-result-score">{score}</span>
      )}
      {result.next_action && (
        <span className="search-result-next-action">{result.next_action}</span>
      )}
    </li>
  );
}
