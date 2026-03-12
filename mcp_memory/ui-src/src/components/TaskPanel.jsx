import { useAppState, useAppDispatch } from '../context/AppContext';
import TaskList from './TaskList';
import TaskForm from './TaskForm';

const FILTERS = [
  { value: '', label: 'All' },
  { value: 'open', label: 'Open' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'blocked', label: 'Blocked' },
  { value: 'done', label: 'Done' },
  { value: 'cancelled', label: 'Cancelled' },
];

function filterTasks(tasks, filter) {
  if (!filter) return tasks;
  return tasks.filter((t) => t.status === filter);
}

export default function TaskPanel({ tasks, projectId, onRefresh }) {
  const state = useAppState();
  const dispatch = useAppDispatch();

  const filteredTasks = filterTasks(tasks ?? [], state.taskFilter);

  function handleFilterClick(value) {
    dispatch({ type: 'SET_TASK_FILTER', value });
  }

  function handleToggleAddForm() {
    dispatch({ type: 'SET_SHOW_ADD_TASK_FORM', value: !state.showAddTaskForm });
  }

  function handleTaskCreated() {
    dispatch({ type: 'SET_SHOW_ADD_TASK_FORM', value: false });
    onRefresh?.();
  }

  return (
    <div data-testid="task-panel">
      <div className="filter-bar">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            className={`filter-btn ${state.taskFilter === f.value ? 'active' : ''}`}
            onClick={() => handleFilterClick(f.value)}
          >
            {f.label}
          </button>
        ))}
        <button
          type="button"
          className="btn btn-primary"
          onClick={handleToggleAddForm}
        >
          {state.showAddTaskForm ? 'Cancel' : '+ Add Task'}
        </button>
      </div>

      {state.showAddTaskForm && (
        <TaskForm
          projectId={projectId}
          task={null}
          onSuccess={handleTaskCreated}
          onCancel={() => dispatch({ type: 'SET_SHOW_ADD_TASK_FORM', value: false })}
        />
      )}

      <TaskList
        tasks={filteredTasks}
        projectId={projectId}
        onRefresh={onRefresh}
      />
    </div>
  );
}
