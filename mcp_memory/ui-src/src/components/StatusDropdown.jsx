import { useState, useEffect, useRef } from 'react';
import { STATUS_OPTIONS, statusEmoji } from '../utils';

export default function StatusDropdown({ currentStatus, onStatusChange }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    function handleClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) {
        setOpen(false);
      }
    }
    document.addEventListener('click', handleClickOutside, true);
    return () => document.removeEventListener('click', handleClickOutside, true);
  }, [open]);

  function handleTriggerClick(e) {
    e.stopPropagation();
    setOpen((prev) => !prev);
  }

  function handleOptionClick(e, status) {
    e.stopPropagation();
    onStatusChange(status);
    setOpen(false);
  }

  return (
    <div className="task-status-dropdown" ref={ref}>
      <button
        className={`task-status-trigger badge-${currentStatus}`}
        onClick={handleTriggerClick}
        type="button"
      >
        {statusEmoji(currentStatus)} {currentStatus}
      </button>
      {open && (
        <div className="task-status-options">
          {STATUS_OPTIONS.map((status) => (
            <div
              key={status}
              className={`status-option badge-${status}${status === currentStatus ? ' active' : ''}`}
              data-value={status}
              onClick={(e) => handleOptionClick(e, status)}
            >
              {status}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
