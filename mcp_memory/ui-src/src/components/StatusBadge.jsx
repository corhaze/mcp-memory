import { statusEmoji } from '../utils';

export default function StatusBadge({ status }) {
  return (
    <span className={`status-badge badge-${status}`}>
      {statusEmoji(status)} {status}
    </span>
  );
}
