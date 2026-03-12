import KanbanCard from './KanbanCard';

export default function KanbanColumn({ status, title, tasks, onDrop, onCardClick }) {
  function handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add('kanban-drop-active');
  }

  function handleDragLeave(e) {
    e.currentTarget.classList.remove('kanban-drop-active');
  }

  function handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('kanban-drop-active');
    const taskId = e.dataTransfer.getData('text/plain');
    if (taskId) {
      onDrop?.(taskId, status);
    }
  }

  return (
    <div
      className="kanban-column"
      data-testid={`kanban-column-${status}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="kanban-column-header">
        <span>{title}</span>
        <span className="kanban-column-count">{tasks.length}</span>
      </div>
      {tasks.map((task) => (
        <KanbanCard
          key={task.id}
          task={task}
          onClick={() => onCardClick?.(task)}
        />
      ))}
    </div>
  );
}
