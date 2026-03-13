import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import DecisionItem from './DecisionItem';

vi.mock('../api', () => ({
  deleteDecision: vi.fn(() => Promise.resolve()),
  updateDecision: vi.fn(() => Promise.resolve()),
  createDecision: vi.fn(() => Promise.resolve()),
}));

import * as api from '../api';

const mockDecision = {
  id: 'd1',
  title: 'Use React',
  status: 'active',
  decision_text: 'We will use React for the frontend.',
  rationale: 'Modern and well-supported.',
  superseded_by: null,
};

function renderItem(decision = mockDecision, onRefresh = vi.fn()) {
  return render(
    <MemoryRouter>
      <DecisionItem decision={decision} projectId="p1" onRefresh={onRefresh} />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('DecisionItem', () => {
  it('renders title and status badge', () => {
    renderItem();
    expect(screen.getByText('Use React')).toBeInTheDocument();
    expect(screen.getByText(/active/)).toBeInTheDocument();
  });

  it('renders decision text as markdown', () => {
    renderItem();
    expect(screen.getByText('We will use React for the frontend.')).toBeInTheDocument();
  });

  it('renders rationale', () => {
    renderItem();
    expect(screen.getByText(/Modern and well-supported/)).toBeInTheDocument();
  });

  it('renders supersedes info when present', () => {
    renderItem({ ...mockDecision, supersedes_decision_id: 'dec-99abc' });
    expect(screen.getByText(/dec-99ab/)).toBeInTheDocument();
  });

  it('edit icon button shows form', () => {
    renderItem();
    fireEvent.click(screen.getByTitle('Edit'));
    expect(screen.getByTestId('decision-form')).toBeInTheDocument();
  });

  it('delete shows confirm dialog and calls API on confirm', async () => {
    const onRefresh = vi.fn();
    renderItem(mockDecision, onRefresh);

    fireEvent.click(screen.getByTitle('Delete'));
    expect(screen.getByTestId('confirm-dialog-overlay')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Confirm'));
    await vi.waitFor(() => {
      expect(api.deleteDecision).toHaveBeenCalledWith('p1', 'd1');
    });
    expect(onRefresh).toHaveBeenCalled();
  });

  it('delete does nothing if user cancels confirm dialog', () => {
    renderItem();
    fireEvent.click(screen.getByTitle('Delete'));
    expect(screen.getByTestId('confirm-dialog-overlay')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Cancel'));
    expect(api.deleteDecision).not.toHaveBeenCalled();
    expect(screen.queryByTestId('confirm-dialog-overlay')).not.toBeInTheDocument();
  });
});
