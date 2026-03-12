import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AppProvider } from '../context/AppContext';
import NoteItem from './NoteItem';

vi.mock('../api', () => ({
  deleteNote: vi.fn(() => Promise.resolve()),
  updateNote: vi.fn(() => Promise.resolve()),
  createNote: vi.fn(() => Promise.resolve()),
}));

const mockNote = {
  id: 'n1',
  title: 'Test Note',
  note_text: 'Some content here.',
  note_type: 'foundation',
  created_at: '2026-03-10T10:00:00Z',
  updated_at: '2026-03-10T10:00:00Z',
};

function renderItem(note = mockNote) {
  return render(
    <MemoryRouter>
      <AppProvider>
        <NoteItem note={note} projectId="p1" projectName="my-project" onRefresh={vi.fn()} />
      </AppProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('NoteItem', () => {
  it('collapsed: shows title and type pill', () => {
    renderItem();
    expect(screen.getByText('Test Note')).toBeInTheDocument();
    expect(screen.getByText('foundation')).toBeInTheDocument();
  });

  it('body is not visible when collapsed', () => {
    renderItem();
    expect(screen.queryByText('Some content here.')).not.toBeInTheDocument();
  });

  it('click expands to show body', () => {
    renderItem();
    fireEvent.click(screen.getByText('Test Note'));
    expect(screen.getByText('Some content here.')).toBeInTheDocument();
  });

  it('View Detail link present when expanded', () => {
    renderItem();
    fireEvent.click(screen.getByText('Test Note'));
    const link = screen.getByText(/View Detail/);
    expect(link).toBeInTheDocument();
    expect(link.closest('a')).toHaveAttribute('href', '/my-project/notes/n1');
  });

  it('does not render type pill when note_type is null', () => {
    renderItem({ ...mockNote, note_type: null });
    expect(screen.queryByText('foundation')).not.toBeInTheDocument();
  });
});
