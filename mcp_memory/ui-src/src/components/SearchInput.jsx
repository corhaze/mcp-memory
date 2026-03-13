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

  return (
    <div className="sidebar-search">
      <input
        type="text"
        placeholder="Search all projects..."
        aria-label="Search"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
      />
    </div>
  );
}
