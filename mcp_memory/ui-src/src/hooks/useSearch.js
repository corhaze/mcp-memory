import { useState, useEffect, useCallback } from 'react';
import { semanticSearch } from '../api';

export function useSearch(query, projectId) {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const search = useCallback(async () => {
    if (!query) {
      setResults(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await semanticSearch(query, projectId);
      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [query, projectId]);

  useEffect(() => {
    search();
  }, [search]);

  return { results, loading, error };
}
