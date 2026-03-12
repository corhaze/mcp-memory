import { useState, useEffect, useCallback } from 'react';
import { getTask } from '../api';

export function useTask(projectId, taskId) {
  const [task, setTask] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    if (!projectId || !taskId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getTask(projectId, taskId);
      setTask(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [projectId, taskId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { task, loading, error, refresh };
}
