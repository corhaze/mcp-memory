import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as api from '../api';
import KanbanColumn from './KanbanColumn';
import TaskForm from './TaskForm';

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

  // Limit done column to 5 most recent, but track total
  const allDone = groups.done;
  allDone.sort((a, b) => {
    const dateA = a.completed_at || a.created_at || '';
    const dateB = b.completed_at || b.created_at || '';
    return dateB.localeCompare(dateA);
  });
  const totalDone = allDone.length;
  groups.done = allDone.slice(0, DONE_LIMIT);

  return { groups, totalDone };
}

export default function KanbanBoard({ tasks, projectId, projectName, onRefresh }) {
  const navigate = useNavigate();
  const [showForm, setShowForm] = useState(false);

  const { groups, totalDone } = groupTasksByStatus(tasks);

  async function handleDrop(taskId, status) {
    await api.updateTask(projectId, taskId, { status });
    onRefresh?.();
  }

  function handleCardClick(task) {
    navigate(`/${projectName}/tasks/${task.id}`);
  }

  function handleTaskCreated() {
    setShowForm(false);
    onRefresh?.();
  }

  return (
    <div data-testid="kanban-board">
      <div className="panel-toolbar">
        <button
          type="button"
          className="filter-btn"
          onClick={() => setShowForm((v) => !v)}
        >
          {showForm ? 'Cancel' : '+ Add Task'}
        </button>
      </div>
      {showForm && (
        <TaskForm
          projectId={projectId}
          task={null}
          onSuccess={handleTaskCreated}
          onCancel={() => setShowForm(false)}
        />
      )}
      <div className="kanban-board">
        {COLUMNS.map((col) => (
          <KanbanColumn
            key={col.status}
            status={col.status}
            title={col.title}
            tasks={groups[col.status]}
            totalCount={col.status === 'done' ? totalDone : null}
            onDrop={handleDrop}
            onCardClick={handleCardClick}
          />
        ))}
      </div>
    </div>
  );
}
