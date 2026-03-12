import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AppProvider } from '../context/AppContext';
import GlobalWorkspace from './GlobalWorkspace';

const mockNotes = [
  { id: 'gn1', title: 'Global Alpha', note_text: 'Alpha body', note_type: 'foundation', created_at: '2026-03-10T10:00:00Z' },
  { id: 'gn2', title: 'Global Beta', note_text: 'Beta body', note_type: null, created_at: '2026-03-10T11:00:00Z' },
];

vi.mock('../hooks/useGlobalNotes', () => ({
  useGlobalNotes: vi.fn(() => ({
    globalNotes: mockNotes,
    loading: false,
    error: null,
    refresh: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
  })),
}));

vi.mock('../api', () => ({
  updateGlobalNote: vi.fn(() => Promise.resolve()),
  deleteGlobalNote: vi.fn(() => Promise.resolve()),
  createGlobalNote: vi.fn(() => Promise.resolve()),
}));

function renderWorkspace() {
  return render(
    <MemoryRouter initialEntries={['/global']}>
      <AppProvider>
        <GlobalWorkspace />
      </AppProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('GlobalWorkspace', () => {
  it('renders header and tab bar', () => {
    renderWorkspace();
    expect(screen.getByText('Global Workspace')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Notes' })).toBeInTheDocument();
  });

  it('renders global notes', () => {
    renderWorkspace();
    expect(screen.getByText('Global Alpha')).toBeInTheDocument();
    expect(screen.getByText('Global Beta')).toBeInTheDocument();
  });

  it('filter bar filters by type', () => {
    renderWorkspace();
    fireEvent.click(screen.getByText('Foundation'));
    expect(screen.getByText('Global Alpha')).toBeInTheDocument();
    expect(screen.queryByText('Global Beta')).not.toBeInTheDocument();
  });

  it('Add Note button shows form', () => {
    renderWorkspace();
    fireEvent.click(screen.getByText('Add Note'));
    expect(screen.getByTestId('global-note-form')).toBeInTheDocument();
  });
});
