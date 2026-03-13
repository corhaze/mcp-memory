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

  const hasMetaBadges = task.urgent || task.complex || (task.subtasks && task.subtasks.length > 0);

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
      <div className="kanban-card-title">{task.title}</div>
      {hasMetaBadges && (
        <div className="kanban-card-meta">
          {task.urgent && <span className="urgent-dot" title="Urgent" />}
          {task.complex && <span className="complex-badge" title="Complex">COMPLEX</span>}
          {task.subtasks && task.subtasks.length > 0 && (
            <span className="kanban-subtask-summary">
              {task.subtasks.filter((s) => s.status === 'done').length}/{task.subtasks.length}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
