import { useParams, useNavigate } from 'react-router-dom';
import { useProjects } from '../hooks/useProjects';
import { useProjectData } from '../hooks/useProjectData';
import StatusBadge from './StatusBadge';
import TabBar from './TabBar';
import TaskPanel from './TaskPanel';
import SummaryPanel from './SummaryPanel';
import DecisionPanel from './DecisionPanel';
import NotePanel from './NotePanel';
import TimelinePanel from './TimelinePanel';

const TABS = [
  { name: 'summary', label: 'Summary' },
  { name: 'tasks', label: 'Tasks' },
  { name: 'board', label: 'Board' },
  { name: 'decisions', label: 'Decisions' },
  { name: 'notes', label: 'Notes' },
  { name: 'timeline', label: 'Timeline' },
];

function TabContent({ activeTab, project, projectName, data }) {
  switch (activeTab) {
    case 'summary':
      return (
        <SummaryPanel
          summary={data.summary}
          projectId={project.id}
          onRefresh={data.refreshSummary}
        />
      );
    case 'tasks':
      return (
        <TaskPanel
          tasks={data.tasks}
          projectId={project.id}
          onRefresh={data.refreshTasks}
        />
      );
    case 'decisions':
      return (
        <DecisionPanel
          decisions={data.decisions}
          projectId={project.id}
          onRefresh={data.refreshDecisions}
        />
      );
    case 'notes':
      return (
        <NotePanel
          notes={data.notes}
          projectId={project.id}
          projectName={projectName}
          onRefresh={data.refreshNotes}
        />
      );
    case 'timeline':
      return (
        <TimelinePanel
          timeline={data.timeline}
          projectName={projectName}
        />
      );
    default:
      return <div>Tab: {activeTab}</div>;
  }
}

export default function ProjectView() {
  const { projectName, tab } = useParams();
  const navigate = useNavigate();
  const { projects, loading: projectsLoading } = useProjects();
  const activeTab = tab || 'summary';

  const project = projects?.find((p) => p.name === projectName) ?? null;
  const data = useProjectData(project?.id ?? null);
  const { loading: dataLoading, error } = data;

  function handleTabClick(tabName) {
    navigate(`/${projectName}/${tabName}`);
  }

  if (projectsLoading || (!project && !projects)) {
    return <div className="empty-state" data-testid="project-loading"><p className="nav-hint">Loading...</p></div>;
  }

  if (projects && !project) {
    return <div className="empty-state"><p className="nav-hint">Project not found.</p></div>;
  }

  return (
    <div data-testid="project-view">
      <header id="project-header">
        <div className="project-title-row">
          <h2 id="project-name">{project.name}</h2>
          {project.status && <StatusBadge status={project.status} />}
        </div>
        {project.description && (
          <p className="project-description">{project.description}</p>
        )}
      </header>

      <TabBar tabs={TABS} activeTab={activeTab} onTabClick={handleTabClick} />

      {dataLoading ? (
        <div className="panel"><p className="nav-hint">Loading...</p></div>
      ) : error ? (
        <div className="panel"><p className="nav-hint">Error: {error}</p></div>
      ) : (
        <section className="panel" data-testid={`panel-${activeTab}`}>
          <TabContent
            activeTab={activeTab}
            project={project}
            projectName={projectName}
            data={data}
          />
        </section>
      )}
    </div>
  );
}
