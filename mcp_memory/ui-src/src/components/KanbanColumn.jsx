import KanbanCard from './KanbanCard';

export default function KanbanColumn({ status, title, tasks, totalCount, onDrop, onCardClick }) {
  function handleDragOver(e) {
    e.preventDefault();
    const body = e.currentTarget;
    body.classList.add('kanban-drop-active');
  }

  function handleDragLeave(e) {
    const body = e.currentTarget;
    if (!body.contains(e.relatedTarget)) {
      body.classList.remove('kanban-drop-active');
    }
  }

  function handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('kanban-drop-active');
    const taskId = e.dataTransfer.getData('text/plain');
    if (taskId) {
      onDrop?.(taskId, status);
    }
  }

  const count = totalCount != null && totalCount !== tasks.length
    ? `${tasks.length}/${totalCount}`
    : tasks.length;

  return (
    <div
      className="kanban-column"
      data-status={status}
      data-testid={`kanban-column-${status}`}
    >
      <div className={`kanban-column-header badge-${status}`}>
        <span>{title}</span>
        <span className="kanban-column-count">{count}</span>
      </div>
      <div
        className="kanban-column-body"
        data-status={status}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {tasks.length > 0 ? (
          tasks.map((task) => (
            <KanbanCard
              key={task.id}
              task={task}
              onClick={() => onCardClick?.(task)}
            />
          ))
        ) : (
          <div className="kanban-drop-placeholder">Drop here</div>
        )}
      </div>
    </div>
  );
}
