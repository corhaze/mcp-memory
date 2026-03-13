import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import * as api from '../api';
import KanbanColumn from './KanbanColumn';
import ProjectFilterBar from './ProjectFilterBar';

const COLUMNS = [
  { status: 'open', title: 'Open' },
  { status: 'in_progress', title: 'In Progress' },
  { status: 'blocked', title: 'Blocked' },
  { status: 'done', title: 'Done' },
];

const DONE_LIMIT = 5;

function groupTasksByStatus(tasks) {
  const groups = { open: [], in_progress: [], blocked: [], done: [] };
  for (const task of tasks) {
    if (groups[task.status]) groups[task.status].push(task);
  }
  const allDone = groups.done.sort((a, b) =>
    (b.completed_at || b.created_at || '').localeCompare(a.completed_at || a.created_at || '')
  );
  const totalDone = allDone.length;
  groups.done = allDone.slice(0, DONE_LIMIT);
  return { groups, totalDone };
}

export default function GlobalBoard() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [selectedProjectIds, setSelectedProjectIds] = useState(null); // null = all

  useEffect(() => {
    api.getProjects().then(setProjects).catch(console.error);
    api.getAllTasks().then(setTasks).catch(console.error);
  }, []);

  // When projects load, default-select all
  useEffect(() => {
    if (projects.length > 0 && selectedProjectIds === null) {
      setSelectedProjectIds(new Set(projects.map((p) => p.id)));
    }
  }, [projects, selectedProjectIds]);

  const visibleTasks =
    selectedProjectIds === null
      ? tasks
      : tasks.filter((t) => selectedProjectIds.has(t.project_id));

  const { groups, totalDone } = groupTasksByStatus(visibleTasks);

  function handleCardClick(task) {
    navigate(`/${task.project_name}/tasks/${task.id}`);
  }

  function toggleProject(projectId) {
    setSelectedProjectIds((prev) => {
      const next = new Set(prev);
      if (next.has(projectId)) next.delete(projectId);
      else next.add(projectId);
      return next;
    });
  }

  return (
    <div data-testid="global-board">
      <ProjectFilterBar
        projects={projects}
        selectedProjectIds={selectedProjectIds ?? new Set()}
        onToggle={toggleProject}
      />
      <div className="kanban-board">
        {COLUMNS.map((col) => (
          <KanbanColumn
            key={col.status}
            status={col.status}
            title={col.title}
            tasks={groups[col.status]}
            totalCount={col.status === 'done' ? totalDone : null}
            onDrop={null}
            onCardClick={handleCardClick}
          />
        ))}
      </div>
    </div>
  );
}
