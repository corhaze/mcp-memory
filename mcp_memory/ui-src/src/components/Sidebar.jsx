import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { useProjects } from '../hooks/useProjects';

export default function Sidebar() {
  const navigate = useNavigate();
  const { projectName } = useParams();
  const location = useLocation();
  const { projects, loading, error } = useProjects();

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

      <div className="sidebar-search">
        <input
          type="text"
          placeholder="Search all projects..."
          aria-label="Search"
          disabled
        />
      </div>

      <div className="global-notes-section">
        <button
          className={`global-workspace-nav-item${isGlobalActive ? ' active' : ''}`}
          onClick={() => navigate('/global')}
        >
          <span className="nav-section-label">// global workspace</span>
        </button>
      </div>

      <div className="sidebar-section-header">
        <span className="nav-section-label">Projects</span>
      </div>

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
