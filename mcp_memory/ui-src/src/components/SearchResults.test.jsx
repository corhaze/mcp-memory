import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import SearchResults from './SearchResults';
import { useSearch } from '../hooks/useSearch';

const mockResults = {
  results: [
    { id: 't1', entity_type: 'task', title: 'Build widget', score: 0.92, project_name: 'proj', status: 'open' },
    { id: 'n1', entity_type: 'global_note', title: 'Design doc', score: 0.85, project_name: null, note_type: 'foundation' },
  ],
  embeddings_available: true,
};

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock('../hooks/useSearch', () => ({
  useSearch: vi.fn(),
}));

function renderResults(query = 'test', projectId = 'p1') {
  return render(
    <MemoryRouter>
      <SearchResults query={query} projectId={projectId} />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  useSearch.mockReturnValue({ results: mockResults, loading: false, error: null });
});

describe('SearchResults', () => {
  it('renders result items', () => {
    renderResults();
    expect(screen.getByText('Build widget')).toBeInTheDocument();
    expect(screen.getByText('Design doc')).toBeInTheDocument();
  });

  it('shows score as percentage', () => {
    renderResults();
    expect(screen.getByText('92%')).toBeInTheDocument();
    expect(screen.getByText('85%')).toBeInTheDocument();
  });

  it('shows empty state for no results', () => {
    useSearch.mockReturnValue({
      results: { results: [], embeddings_available: true },
      loading: false,
      error: null,
    });

    renderResults();
    expect(screen.getByText('No results found.')).toBeInTheDocument();
  });

  it('click navigates to entity', () => {
    renderResults();
    fireEvent.click(screen.getByText('Build widget'));
    expect(mockNavigate).toHaveBeenCalledWith('/proj/tasks');
  });
});
