import { useEffect, useCallback } from 'react';

export default function ConfirmDialog({ message, confirmLabel = 'Confirm', cancelLabel = 'Cancel', onConfirm, onCancel }) {
  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === 'Escape') onCancel();
    },
    [onCancel],
  );

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  function handleOverlayClick(e) {
    if (e.target === e.currentTarget) onCancel();
  }

  return (
    <div className="modal-overlay" onClick={handleOverlayClick} data-testid="confirm-dialog-overlay">
      <div className="modal-container confirm-dialog" role="alertdialog" aria-modal="true">
        <div className="modal-body">
          <p className="confirm-dialog-message">{message}</p>
          <div className="confirm-dialog-actions">
            <button type="button" className="btn btn-primary" onClick={onConfirm}>
              {confirmLabel}
            </button>
            <button type="button" className="btn btn-secondary" onClick={onCancel}>
              {cancelLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
