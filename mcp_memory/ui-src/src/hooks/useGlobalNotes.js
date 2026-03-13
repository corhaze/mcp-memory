import { useState, useEffect, useCallback } from 'react';
import * as api from '../api';

export function useGlobalNotes() {
  const [globalNotes, setGlobalNotes] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getGlobalNotes();
      setGlobalNotes(data.items);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const create = useCallback(async (data) => {
    const result = await api.createGlobalNote(data);
    await refresh();
    return result;
  }, [refresh]);

  const update = useCallback(async (noteId, data) => {
    const result = await api.updateGlobalNote(noteId, data);
    await refresh();
    return result;
  }, [refresh]);

  const remove = useCallback(async (noteId) => {
    await api.deleteGlobalNote(noteId);
    await refresh();
  }, [refresh]);

  return { globalNotes, loading, error, refresh, create, update, remove };
}
