import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import TimelinePanel from './TimelinePanel';

const mockTimeline = [
  {
    id: 'e1',
    event_type: 'status_change',
    task_id: 't1',
    task_title: 'Build the widget',
    event_note: 'Changed to in_progress',
    created_at: '2026-03-10T12:00:00Z',
  },
  {
    id: 'e2',
    event_type: 'created',
    task_id: 't2',
    task_title: 'Fix the bug',
    event_note: null,
    created_at: '2026-03-09T08:00:00Z',
  },
];

function renderPanel(timeline = mockTimeline) {
  return render(
    <MemoryRouter>
      <TimelinePanel timeline={timeline} projectName="my-project" />
    </MemoryRouter>,
  );
}

describe('TimelinePanel', () => {
  it('renders events with task titles', () => {
    renderPanel();
    expect(screen.getByText('Build the widget')).toBeInTheDocument();
    expect(screen.getByText('Fix the bug')).toBeInTheDocument();
  });

  it('task titles are links to task detail', () => {
    renderPanel();
    const link = screen.getByText('Build the widget');
    expect(link.closest('a')).toHaveAttribute('href', '/my-project/tasks/t1');
  });

  it('renders event type badges', () => {
    renderPanel();
    expect(screen.getByText('status_change')).toBeInTheDocument();
    expect(screen.getByText('created')).toBeInTheDocument();
  });

  it('renders event notes when present', () => {
    renderPanel();
    expect(screen.getByText('Changed to in_progress')).toBeInTheDocument();
  });

  it('shows empty state message', () => {
    renderPanel([]);
    expect(screen.getByText('No events yet.')).toBeInTheDocument();
  });

  it('shows empty state for null timeline', () => {
    renderPanel(null);
    expect(screen.getByText('No events yet.')).toBeInTheDocument();
  });
});
