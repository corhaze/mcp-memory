/* components/kanban.js — Kanban board rendering and drag-and-drop */

import { els } from '../dom.js';
import { state } from '../state.js';
import { esc } from '../utils.js';

const COLUMNS = ['open', 'in_progress', 'blocked', 'done', 'cancelled'];

const COLUMN_LABELS = {
    open: 'Open',
    in_progress: 'In Progress',
    blocked: 'Blocked',
    done: 'Done',
    cancelled: 'Cancelled',
};

// Module-level drag state
let _draggedTaskId = null;
let _didDrag = false;

function cardMeta(task) {
    const parts = [];
    if (task.urgent) {
        parts.push('<span class="urgent-dot" title="Urgent"></span>');
    }
    if (task.complex) {
        parts.push('<span class="complex-badge" title="Complex">COMPLEX</span>');
    }
    if (task.subtasks && task.subtasks.length > 0) {
        const done = task.subtasks.filter(s => s.status === 'done').length;
        parts.push(`<span class="kanban-subtask-summary">${done}/${task.subtasks.length}</span>`);
    }
    return parts.length
        ? `<div class="kanban-card-meta">${parts.join('')}</div>`
        : '';
}

function renderCard(task) {
    return `
        <div class="kanban-card" draggable="true" data-task-id="${esc(task.id)}">
            <div class="kanban-card-title">${esc(task.title)}</div>
            ${cardMeta(task)}
        </div>`;
}

function renderColumn(status, tasks) {
    const cards = tasks.length
        ? tasks.map(renderCard).join('')
        : '<div class="kanban-drop-placeholder">Drop here</div>';

    return `
        <div class="kanban-column" data-status="${status}">
            <div class="kanban-column-header badge-${status}">
                <span>${COLUMN_LABELS[status]}</span>
                <span class="kanban-column-count">${tasks.length}</span>
            </div>
            <div class="kanban-column-body" data-status="${status}">
                ${cards}
            </div>
        </div>`;
}

export function renderKanban() {
    const topLevel = state.tasks.filter(t => !t.parent_task_id);

    const byStatus = new Map(COLUMNS.map(s => [s, []]));
    for (const task of topLevel) {
        const col = byStatus.get(task.status);
        if (col) col.push(task);
    }

    els.kanbanBoard.innerHTML = COLUMNS
        .map(status => renderColumn(status, byStatus.get(status)))
        .join('');
}

export function bindKanbanEvents(onStatusChange, onCardClick) {
    const board = els.kanbanBoard;

    board.addEventListener('dragstart', e => {
        const card = e.target.closest('.kanban-card');
        if (!card) return;
        _draggedTaskId = card.dataset.taskId;
        _didDrag = true;
        e.dataTransfer.setData('text/plain', _draggedTaskId);
        e.dataTransfer.effectAllowed = 'move';
        // Use requestAnimationFrame so the dragging class doesn't prevent
        // the browser from taking a snapshot for the drag image.
        requestAnimationFrame(() => card.classList.add('dragging'));
    });

    board.addEventListener('dragend', e => {
        const card = e.target.closest('.kanban-card');
        if (card) card.classList.remove('dragging');
        board.querySelectorAll('.kanban-column-body').forEach(b =>
            b.classList.remove('kanban-drop-active')
        );
        _draggedTaskId = null;
        // Reset _didDrag after a tick so the click handler can check it first.
        setTimeout(() => { _didDrag = false; }, 0);
    });

    board.addEventListener('dragover', e => {
        const body = e.target.closest('.kanban-column-body');
        if (!body) return;
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        // Remove highlight from any other column first.
        board.querySelectorAll('.kanban-column-body').forEach(b =>
            b.classList.remove('kanban-drop-active')
        );
        body.classList.add('kanban-drop-active');
    });

    board.addEventListener('dragleave', e => {
        const body = e.target.closest('.kanban-column-body');
        if (!body) return;
        // Only remove if we've truly left the column body (not entered a child).
        if (!body.contains(e.relatedTarget)) {
            body.classList.remove('kanban-drop-active');
        }
    });

    board.addEventListener('drop', e => {
        const body = e.target.closest('.kanban-column-body');
        if (!body) return;
        e.preventDefault();
        body.classList.remove('kanban-drop-active');

        const taskId = e.dataTransfer.getData('text/plain') || _draggedTaskId;
        const newStatus = body.dataset.status;
        if (!taskId || !newStatus) return;

        // Find current status to avoid no-op API calls.
        const task = state.tasks.find(t => t.id === taskId);
        if (task && task.status === newStatus) return;

        onStatusChange(taskId, newStatus);
    });

    board.addEventListener('click', e => {
        if (_didDrag) return;
        const card = e.target.closest('.kanban-card');
        if (!card) return;
        onCardClick(card.dataset.taskId);
    });
}
