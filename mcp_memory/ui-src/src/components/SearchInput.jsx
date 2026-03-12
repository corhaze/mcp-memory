import { useState } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';

export default function SearchInput() {
  const [value, setValue] = useState('');
  const navigate = useNavigate();
  const { projectName } = useParams();
  const location = useLocation();

  const isGlobal = location.pathname.startsWith('/global');

  function handleKeyDown(e) {
    if (e.key !== 'Enter') return;
    e.preventDefault();
    const q = value.trim();
    if (!q) return;

    const basePath = projectName ? `/${projectName}` : isGlobal ? '/global' : '/';
    navigate(`${basePath}?q=${encodeURIComponent(q)}`);
  }

  function handleClear() {
    setValue('');
    const basePath = projectName ? `/${projectName}` : isGlobal ? '/global' : '/';
    navigate(basePath);
  }

  return (
    <div className="sidebar-search">
      <div className="search-input-wrapper">
        <input
          type="text"
          placeholder="Search all projects..."
          aria-label="Search"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        {value && (
          <button
            className="search-clear-btn"
            onClick={handleClear}
            aria-label="Clear search"
            type="button"
          >
            &times;
          </button>
        )}
      </div>
    </div>
  );
}
