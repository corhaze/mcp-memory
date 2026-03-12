import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AppProvider } from '../context/AppContext';
import GlobalNoteItem from './GlobalNoteItem';

vi.mock('../api', () => ({
  updateGlobalNote: vi.fn(() => Promise.resolve()),
  deleteGlobalNote: vi.fn(() => Promise.resolve()),
}));

const mockNote = {
  id: 'gn1',
  title: 'Test Global Note',
  note_text: 'Some global content.',
  note_type: 'foundation',
  created_at: '2026-03-10T10:00:00Z',
  updated_at: '2026-03-10T10:00:00Z',
};

function renderItem(note = mockNote) {
  return render(
    <MemoryRouter>
      <AppProvider>
        <GlobalNoteItem note={note} onRefresh={vi.fn()} />
      </AppProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('GlobalNoteItem', () => {
  it('collapsed: shows title and type pill', () => {
    renderItem();
    expect(screen.getByText('Test Global Note')).toBeInTheDocument();
    expect(screen.getByText('foundation')).toBeInTheDocument();
  });

  it('body is not visible when collapsed', () => {
    renderItem();
    expect(screen.queryByText('Some global content.')).not.toBeInTheDocument();
  });

  it('click expands to show body', () => {
    renderItem();
    fireEvent.click(screen.getByText('Test Global Note'));
    expect(screen.getByText('Some global content.')).toBeInTheDocument();
  });

  it('edit toggle shows form fields', () => {
    renderItem();
    fireEvent.click(screen.getByText('Test Global Note'));
    fireEvent.click(screen.getByText('Edit'));
    expect(screen.getByTestId('global-note-edit-form')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Test Global Note')).toBeInTheDocument();
  });

  it('does not render type pill when note_type is null', () => {
    renderItem({ ...mockNote, note_type: null });
    expect(screen.queryByText('foundation')).not.toBeInTheDocument();
  });
});
