import { useEffect, useCallback } from 'react';

export default function Modal({ isOpen, onClose, title, children }) {
  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === 'Escape') onClose();
    },
    [onClose],
  );

  useEffect(() => {
    if (!isOpen) return;
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  function handleOverlayClick(e) {
    if (e.target === e.currentTarget) onClose();
  }

  return (
    <div className="modal-overlay" onClick={handleOverlayClick} data-testid="modal-overlay">
      <div className="modal-container" role="dialog" aria-modal="true">
        <div className="modal-header">
          <h3>{title}</h3>
          <button
            className="modal-close-btn"
            onClick={onClose}
            aria-label="Close"
            type="button"
          >
            &times;
          </button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}
