import { useState } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { useProjects } from '../hooks/useProjects';
import SearchInput from './SearchInput';
import * as api from '../api';

export default function Sidebar() {
  const navigate = useNavigate();
  const { projectName } = useParams();
  const location = useLocation();
  const { projects, loading, error, refresh } = useProjects();

  const [showNewProject, setShowNewProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [creating, setCreating] = useState(false);

  async function handleCreateProject(e) {
    e.preventDefault();
    const name = newProjectName.trim();
    if (!name) return;
    setCreating(true);
    try {
      await api.createProject({ name });
      setNewProjectName('');
      setShowNewProject(false);
      await refresh();
      navigate(`/${name}`);
    } finally {
      setCreating(false);
    }
  }

  const isGlobalActive = location.pathname.startsWith('/global');

  return (
    <aside id="sidebar">
      <div className="sidebar-header">
        <div className="header-main">
          <div className="sidebar-logo-box">
            <span className="logo-epoch">Epoch</span>
          </div>
        </div>
      </div>

      <SearchInput />

      <div className="global-notes-section">
        <button
          className={`global-workspace-nav-item${isGlobalActive ? ' active' : ''}`}
          onClick={() => navigate('/global')}
        >
          // global workspace
        </button>
      </div>

      <div className="sidebar-section-header">
        <span className="nav-section-label">Projects</span>
        <button
          type="button"
          className="icon-btn"
          title="New project"
          onClick={() => { setShowNewProject((v) => !v); setNewProjectName(''); }}
        >+</button>
      </div>

      {showNewProject && (
        <form className="sidebar-new-project-form" onSubmit={handleCreateProject}>
          <input
            type="text"
            className="sidebar-new-project-input"
            placeholder="project-name"
            value={newProjectName}
            onChange={(e) => setNewProjectName(e.target.value)}
            autoFocus
          />
          <button type="submit" className="icon-btn" disabled={creating} title="Create">↵</button>
        </form>
      )}

      <nav id="project-list" aria-label="Projects">
        {loading && <p className="nav-hint">Loading projects...</p>}
        {error && <p className="nav-hint">Error: {error}</p>}
        {projects && projects.length === 0 && (
          <p className="nav-hint">No projects yet.</p>
        )}
        {projects && projects.map((project) => (
          <button
            key={project.id}
            className={`project-nav-item${project.name === projectName ? ' active' : ''}`}
            onClick={() => navigate(`/${project.name}`)}
          >
            {project.name}
          </button>
        ))}
      </nav>
    </aside>
  );
}
