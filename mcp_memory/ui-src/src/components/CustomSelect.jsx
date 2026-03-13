import { useState, useEffect, useRef } from 'react';

/**
 * Fully custom select dropdown matching the terminal aesthetic.
 * Replaces native <select> to avoid OS-specific styling.
 *
 * @param {string}   value       - Current selected value
 * @param {function} onChange    - Called with the new value string
 * @param {Array}    options     - Array of { value, label, className? } objects
 * @param {string}   [placeholder] - Shown when value is empty
 */
export default function CustomSelect({ value, onChange, options, placeholder }) {
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

  const selected = options.find((o) => o.value === value);
  const selectedLabel = selected?.label ?? placeholder ?? '';
  const triggerExtra = selected?.className ?? '';

  return (
    <div className="custom-select" ref={ref}>
      <button
        className={`custom-select-trigger${triggerExtra ? ` ${triggerExtra}` : ''}`}
        onClick={(e) => { e.stopPropagation(); setOpen((v) => !v); }}
        type="button"
      >
        <span className={value ? 'custom-select-value' : 'custom-select-placeholder'}>
          {selectedLabel}
        </span>
        <span className="custom-select-chevron">▾</span>
      </button>
      {open && (
        <div className="custom-select-options">
          {options.map((opt) => (
            <div
              key={opt.value}
              className={`custom-select-option${opt.value === value ? ' active' : ''}${opt.className ? ` ${opt.className}` : ''}`}
              onClick={(e) => { e.stopPropagation(); onChange(opt.value); setOpen(false); }}
            >
              {opt.label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
