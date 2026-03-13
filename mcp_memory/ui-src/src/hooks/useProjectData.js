import { useState, useEffect, useCallback } from 'react';
import {
  getProjectTasks,
  getProjectDecisions,
  getProjectNotes,
  getTimeline,
  getProjectSummary,
} from '../api';

export function useProjectData(projectId) {
  const [tasks, setTasks] = useState(null);
  const [decisions, setDecisions] = useState(null);
  const [notes, setNotes] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refreshTasks = useCallback(async () => {
    if (!projectId) return;
    const data = await getProjectTasks(projectId);
    setTasks(data.items);
  }, [projectId]);

  const refreshDecisions = useCallback(async () => {
    if (!projectId) return;
    const data = await getProjectDecisions(projectId);
    setDecisions(data.items);
  }, [projectId]);

  const refreshNotes = useCallback(async () => {
    if (!projectId) return;
    const data = await getProjectNotes(projectId);
    setNotes(data.items);
  }, [projectId]);

  const refreshTimeline = useCallback(async () => {
    if (!projectId) return;
    const data = await getTimeline(projectId);
    setTimeline(data);
  }, [projectId]);

  const refreshSummary = useCallback(async () => {
    if (!projectId) return;
    const data = await getProjectSummary(projectId);
    setSummary(data);
  }, [projectId]);

  const refresh = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const results = await Promise.all([
        getProjectTasks(projectId),
        getProjectDecisions(projectId),
        getProjectNotes(projectId),
        getTimeline(projectId),
        getProjectSummary(projectId),
      ]);
      setTasks(results[0].items);
      setDecisions(results[1].items);
      setNotes(results[2].items);
      setTimeline(results[3]);
      setSummary(results[4]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return {
    tasks,
    decisions,
    notes,
    timeline,
    summary,
    loading,
    error,
    refresh,
    refreshTasks,
    refreshDecisions,
    refreshNotes,
    refreshTimeline,
    refreshSummary,
  };
}
