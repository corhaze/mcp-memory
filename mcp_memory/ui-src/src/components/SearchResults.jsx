import { useSearch } from '../hooks/useSearch';
import SearchResultItem from './SearchResultItem';

export default function SearchResults({ query, projectId }) {
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
      <h3 className="search-results-heading">
        Results for &ldquo;{query}&rdquo; ({items.length})
      </h3>

      {!embeddingsAvailable && (
        <p className="nav-hint">
          Embeddings are not available. Install FastEmbed for semantic search.
        </p>
      )}

      {items.length === 0 ? (
        <p className="nav-hint">No results found.</p>
      ) : (
        items.map((r) => (
          <SearchResultItem key={`${r.entity_type}-${r.id}`} result={r} />
        ))
      )}
    </div>
  );
}
