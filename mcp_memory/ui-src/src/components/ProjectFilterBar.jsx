export default function ProjectFilterBar({ projects, selectedProjectIds, onToggle }) {
  if (!projects || projects.length === 0) return null;

  return (
    <div className="project-filter-bar" data-testid="project-filter-bar">
      {projects.map((project) => (
        <button
          key={project.id}
          type="button"
          className={`project-filter-btn${selectedProjectIds.has(project.id) ? ' active' : ''}`}
          onClick={() => onToggle(project.id)}
        >
          {project.name}
        </button>
      ))}
    </div>
  );
}
