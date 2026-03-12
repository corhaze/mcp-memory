import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import MarkdownBody from './MarkdownBody';
import { formatRelativeTime } from '../utils';
import { useProjects } from '../hooks/useProjects';
import * as api from '../api';

export default function NoteDetail() {
  const { projectName, noteId } = useParams();
  const navigate = useNavigate();
  const isGlobal = !projectName || projectName === 'global';

  const { projects } = useProjects();
  const project = isGlobal ? null : projects?.find((p) => p.name === projectName) ?? null;

  const [note, setNote] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        let data;
        if (isGlobal) {
          data = await api.getGlobalNote(noteId);
        } else if (project) {
          const notes = await api.getProjectNotes(project.id);
          data = notes.find((n) => n.id === noteId) ?? null;
          if (!data) throw new Error('Note not found');
        } else {
          return; // wait for project to resolve
        }
        if (!cancelled) setNote(data);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [noteId, isGlobal, project]);

  async function handleDelete() {
    if (!window.confirm(`Delete note "${note.title}"?`)) return;
    if (isGlobal) {
      await api.deleteGlobalNote(note.id);
      navigate('/global');
    } else {
      await api.deleteNote(project.id, note.id);
      navigate(`/${projectName}/notes`);
    }
  }

  const backLink = isGlobal ? '/global' : `/${projectName}/notes`;
  const backLabel = isGlobal ? 'Global Workspace' : `${projectName} / Notes`;

  if (loading) {
    return <div className="panel"><p className="nav-hint">Loading note...</p></div>;
  }

  if (error) {
    return (
      <div className="panel">
        <Link to={backLink}>&larr; Back to {backLabel}</Link>
        <p className="nav-hint">Error: {error}</p>
      </div>
    );
  }

  if (!note) {
    return (
      <div className="panel">
        <Link to={backLink}>&larr; Back to {backLabel}</Link>
        <p className="nav-hint">Note not found.</p>
      </div>
    );
  }

  return (
    <div className="note-detail" data-testid="note-detail">
      <Link to={backLink} className="back-link">&larr; Back to {backLabel}</Link>

      <header className="note-detail-header">
        <h2>{note.title}</h2>
        {note.note_type && <span className="note-type-pill">{note.note_type}</span>}
      </header>

      <div className="note-detail-meta">
        {note.created_at && <span>Created {formatRelativeTime(note.created_at)}</span>}
        {note.updated_at && note.updated_at !== note.created_at && (
          <span> · Updated {formatRelativeTime(note.updated_at)}</span>
        )}
      </div>

      <MarkdownBody content={note.note_text} />

      <div className="item-actions">
        <button className="btn btn-sm btn-danger" onClick={handleDelete}>Delete</button>
      </div>
    </div>
  );
}
