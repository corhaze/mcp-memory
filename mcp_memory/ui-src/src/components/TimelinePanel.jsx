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
      <div className="panel-toolbar">
        <span className="panel-label">Task Event Log</span>
      </div>
      <ul className="timeline-list">
        {timeline.map((event, i) => (
          <li key={event.id || i} className="timeline-item">
            <div className="timeline-content">
              <span className="timeline-event-type">{event.event_type || event.type}</span>
              {event.task_id && (
                <div className="timeline-task-title">
                  <Link to={`/${projectName}/tasks/${event.task_id}`}>
                    {event.task_title || event.task_id}
                  </Link>
                </div>
              )}
              {event.event_note && (
                <div className="timeline-note">{event.event_note}</div>
              )}
            </div>
            <div className="timeline-time">
              {formatRelativeTime(event.created_at || event.timestamp)}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
