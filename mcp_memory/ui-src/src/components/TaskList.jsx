import TaskItem from './TaskItem';

export default function TaskList({ tasks, projectId, depth = 0, onRefresh }) {
  if (!tasks || tasks.length === 0) {
    if (depth === 0) {
      return <p className="nav-hint" data-testid="task-list-empty">No tasks found.</p>;
    }
    return null;
  }

  return (
    <div
      className="task-list"
      style={{ marginLeft: depth > 0 ? `${depth * 1.5}rem` : 0 }}
      data-testid="task-list"
    >
      {tasks.map((task) => (
        <TaskItem
          key={task.id}
          task={task}
          projectId={projectId}
          depth={depth}
          onRefresh={onRefresh}
        />
      ))}
    </div>
  );
}
