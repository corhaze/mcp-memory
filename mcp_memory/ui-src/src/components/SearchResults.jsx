import { useSearch } from '../hooks/useSearch';
import SearchResultItem from './SearchResultItem';

export default function SearchResults({ query, projectId, onClear }) {
  const { results, loading, error } = useSearch(query, projectId);

  if (loading) {
    return <p className="nav-hint">Searching...</p>;
  }

  if (error) {
    return <p className="nav-hint">Search error: {error}</p>;
  }

  if (!results) {
    return null;
  }

  const items = results.results || [];
  const embeddingsAvailable = results.embeddings_available !== false;

  return (
    <div data-testid="search-results">
      <div className="panel-toolbar">
        <div className="panel-info">
          <span className="panel-label">Semantic Search Results</span>
        </div>
        <div className="filter-group">
          {onClear && (
            <button type="button" className="filter-btn" onClick={onClear}>
              Clear Search
            </button>
          )}
        </div>
      </div>

      <div className="search-results">
        {!embeddingsAvailable && (
          <p className="search-embeddings-notice">
            Semantic search unavailable — keyword search not yet supported in UI.
          </p>
        )}

        <ul className="search-results-list" aria-live="polite">
          {items.map((r) => (
            <SearchResultItem key={`${r.entity_type}-${r.id}`} result={r} />
          ))}
        </ul>

        {items.length === 0 && embeddingsAvailable && (
          <p className="nav-hint" style={{ padding: '1rem' }}>No results found.</p>
        )}
      </div>
    </div>
  );
}
