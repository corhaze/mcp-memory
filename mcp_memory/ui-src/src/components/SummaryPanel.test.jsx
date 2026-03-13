import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import SummaryPanel from './SummaryPanel';

vi.mock('../api', () => ({
  updateProjectSummary: vi.fn(() => Promise.resolve()),
}));

import * as api from '../api';

beforeEach(() => {
  vi.clearAllMocks();
});

describe('SummaryPanel', () => {
  it('renders markdown summary', () => {
    render(<SummaryPanel summary="**bold summary**" projectId="p1" onRefresh={vi.fn()} />);
    const strong = screen.getByText('bold summary');
    expect(strong.tagName).toBe('STRONG');
  });

  it('shows empty message when no summary', () => {
    render(<SummaryPanel summary="" projectId="p1" onRefresh={vi.fn()} />);
    expect(screen.getByText('No summary yet.')).toBeInTheDocument();
  });

  it('edit toggle shows textarea', () => {
    render(<SummaryPanel summary="Hello world" projectId="p1" onRefresh={vi.fn()} />);
    fireEvent.click(screen.getByText('✎ EDIT'));
    expect(screen.getByTestId('summary-textarea')).toBeInTheDocument();
    expect(screen.getByTestId('summary-textarea').value).toBe('Hello world');
  });

  it('save calls API and refreshes', async () => {
    const onRefresh = vi.fn();
    render(<SummaryPanel summary="Old text" projectId="p1" onRefresh={onRefresh} />);
    fireEvent.click(screen.getByText('✎ EDIT'));
    fireEvent.change(screen.getByTestId('summary-textarea'), {
      target: { value: 'New text' },
    });
    fireEvent.click(screen.getByText('Save'));

    await waitFor(() => {
      expect(api.updateProjectSummary).toHaveBeenCalledWith('p1', 'New text');
    });
    expect(onRefresh).toHaveBeenCalled();
  });

  it('cancel discards changes', () => {
    render(<SummaryPanel summary="Original" projectId="p1" onRefresh={vi.fn()} />);
    fireEvent.click(screen.getByText('✎ EDIT'));
    fireEvent.change(screen.getByTestId('summary-textarea'), {
      target: { value: 'Changed' },
    });
    fireEvent.click(screen.getByText('Cancel'));
    // should be back in view mode with original text
    expect(screen.queryByTestId('summary-textarea')).not.toBeInTheDocument();
    expect(screen.getByText('Original')).toBeInTheDocument();
  });

  it('handles summary as object with text property', () => {
    render(<SummaryPanel summary={{ text: 'From object' }} projectId="p1" onRefresh={vi.fn()} />);
    expect(screen.getByText('From object')).toBeInTheDocument();
  });
});
