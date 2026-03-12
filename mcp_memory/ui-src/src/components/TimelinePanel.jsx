import { Link } from 'react-router-dom';
import { formatRelativeTime } from '../utils';

export default function TimelinePanel({ timeline, projectName }) {
  if (!timeline || timeline.length === 0) {
    return (
      <div data-testid="timeline-panel">
        <p className="nav-hint">No events yet.</p>
      </div>
    );
  }

  return (
    <div data-testid="timeline-panel">
      <ul className="timeline-list">
        {timeline.map((event, i) => (
          <li key={event.id || i} className="timeline-event">
            <span className="timeline-type-badge">{event.event_type || event.type}</span>
            {event.task_id && (
              <Link to={`/${projectName}/tasks/${event.task_id}`} className="timeline-task-link">
                {event.task_title || event.task_id}
              </Link>
            )}
            {event.event_note && (
              <span className="timeline-note">{event.event_note}</span>
            )}
            <span className="timeline-time">
              {formatRelativeTime(event.created_at || event.timestamp)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
