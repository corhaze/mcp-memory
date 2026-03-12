import { useNavigate } from 'react-router-dom';
import * as api from '../api';
import KanbanColumn from './KanbanColumn';

const COLUMNS = [
  { status: 'open', title: 'Open' },
  { status: 'in_progress', title: 'In Progress' },
  { status: 'blocked', title: 'Blocked' },
  { status: 'done', title: 'Done' },
];

const DONE_LIMIT = 5;

function groupTasksByStatus(tasks) {
  const topLevel = (tasks ?? []).filter((t) => !t.parent_task_id);

  const groups = {
    open: [],
    in_progress: [],
    blocked: [],
    done: [],
  };

  for (const task of topLevel) {
    if (groups[task.status]) {
      groups[task.status].push(task);
    }
  }

  // Limit done column to 5 most recent
  groups.done.sort((a, b) => {
    const dateA = a.completed_at || a.created_at || '';
    const dateB = b.completed_at || b.created_at || '';
    return dateB.localeCompare(dateA);
  });
  groups.done = groups.done.slice(0, DONE_LIMIT);

  return groups;
}

export default function KanbanBoard({ tasks, projectId, projectName, onRefresh }) {
  const navigate = useNavigate();

  const groups = groupTasksByStatus(tasks);

  async function handleDrop(taskId, status) {
    await api.updateTask(projectId, taskId, { status });
    onRefresh?.();
  }

  function handleCardClick(task) {
    navigate(`/${projectName}/tasks/${task.id}`);
  }

  return (
    <div className="kanban-board" data-testid="kanban-board">
      {COLUMNS.map((col) => (
        <KanbanColumn
          key={col.status}
          status={col.status}
          title={col.title}
          tasks={groups[col.status]}
          onDrop={handleDrop}
          onCardClick={handleCardClick}
        />
      ))}
    </div>
  );
}
