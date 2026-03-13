import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import TaskNoteList from './TaskNoteList';

vi.mock('../api', () => ({
  getTaskNotes: vi.fn(() => Promise.resolve([])),
}));

vi.mock('./TaskNoteForm', () => ({
  default: () => <div>TaskNoteForm</div>,
}));

const mockNotes = [
  { id: 'n1', title: 'Note Alpha', note_text: 'Body of note alpha', note_type: 'info' },
  { id: 'n2', title: 'Note Beta', note_text: 'Body of note beta', note_type: null },
  { id: 'n3', title: 'Note Gamma', note_text: null, note_type: null },
];

function renderNoteList(notes = mockNotes, props = {}) {
  return render(<TaskNoteList notes={notes} bare {...props} />);
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('TaskNoteList accordion', () => {
  it('renders note titles but no note text by default', () => {
    renderNoteList();

    expect(screen.getByText('Note Alpha')).toBeInTheDocument();
    expect(screen.getByText('Note Beta')).toBeInTheDocument();
    expect(screen.getByText('Note Gamma')).toBeInTheDocument();

    expect(screen.queryByText('Body of note alpha')).not.toBeInTheDocument();
    expect(screen.queryByText('Body of note beta')).not.toBeInTheDocument();
  });

  it('clicking › expands and shows note text', () => {
    renderNoteList();

    const toggles = screen.getAllByRole('button', { name: '›' });
    fireEvent.click(toggles[0]);

    expect(screen.getByText('Body of note alpha')).toBeInTheDocument();
    expect(screen.queryByText('Body of note beta')).not.toBeInTheDocument();
  });

  it('clicking › again collapses the note text', () => {
    renderNoteList();

    const toggles = screen.getAllByRole('button', { name: '›' });
    fireEvent.click(toggles[0]);
    expect(screen.getByText('Body of note alpha')).toBeInTheDocument();

    fireEvent.click(toggles[0]);
    expect(screen.queryByText('Body of note alpha')).not.toBeInTheDocument();
  });

  it('note with no note_text does not show body even when toggled', () => {
    renderNoteList();

    const toggles = screen.getAllByRole('button', { name: '›' });
    // toggles[2] corresponds to Note Gamma which has note_text: null
    fireEvent.click(toggles[2]);

    const container = screen.getByTestId('task-note-list');
    // Only two notes have text — neither should appear; confirm no stray paragraph
    const paragraphs = container.querySelectorAll('p.task-note-text');
    expect(paragraphs).toHaveLength(0);
  });

  it('toggle button gains open class when expanded, loses it when collapsed', () => {
    renderNoteList();

    const toggles = screen.getAllByRole('button', { name: '›' });
    expect(toggles[0]).not.toHaveClass('open');

    fireEvent.click(toggles[0]);
    expect(toggles[0]).toHaveClass('open');

    fireEvent.click(toggles[0]);
    expect(toggles[0]).not.toHaveClass('open');
  });
});
