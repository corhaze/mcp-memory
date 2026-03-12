import { useRef } from 'react';

export default function KanbanCard({ task, onDragStart, onDragEnd, onClick }) {
  const didDrag = useRef(false);

  function handleDragStart(e) {
    didDrag.current = false;
    e.dataTransfer.setData('text/plain', task.id);
    e.currentTarget.classList.add('dragging');
    onDragStart?.(e);
  }

  function handleDrag() {
    didDrag.current = true;
  }

  function handleDragEnd(e) {
    e.currentTarget.classList.remove('dragging');
    onDragEnd?.(e);
  }

  function handleClick() {
    if (!didDrag.current) {
      onClick?.(task);
    }
  }

  const truncatedAction = task.next_action
    ? task.next_action.length > 80
      ? task.next_action.slice(0, 80) + '...'
      : task.next_action
    : null;

  return (
    <div
      className="kanban-card"
      data-testid={`kanban-card-${task.id}`}
      draggable="true"
      onDragStart={handleDragStart}
      onDrag={handleDrag}
      onDragEnd={handleDragEnd}
      onClick={handleClick}
    >
      <span className="kanban-card-title">{task.title}</span>
      {task.urgent && <span className="badge badge-urgent">urgent</span>}
      {truncatedAction && (
        <span className="kanban-card-action">{truncatedAction}</span>
      )}
    </div>
  );
}
