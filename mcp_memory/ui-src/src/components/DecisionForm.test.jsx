import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import DecisionForm from './DecisionForm';

vi.mock('../api', () => ({
  createDecision: vi.fn(() => Promise.resolve({ id: 'new' })),
  updateDecision: vi.fn(() => Promise.resolve({ id: 'd1' })),
}));

import * as api from '../api';

beforeEach(() => {
  vi.clearAllMocks();
});

describe('DecisionForm', () => {
  it('creates with correct fields on submit', async () => {
    const onSuccess = vi.fn();
    render(
      <DecisionForm projectId="p1" decision={null} onSuccess={onSuccess} onCancel={vi.fn()} />,
    );

    fireEvent.change(screen.getByPlaceholderText('Decision title'), {
      target: { value: 'New Decision' },
    });
    fireEvent.change(screen.getByPlaceholderText('Decision text (markdown)'), {
      target: { value: 'Some decision text' },
    });
    fireEvent.change(screen.getByPlaceholderText('Rationale'), {
      target: { value: 'Good reasons' },
    });

    fireEvent.click(screen.getByText('Create'));

    await waitFor(() => {
      expect(api.createDecision).toHaveBeenCalledWith('p1', {
        title: 'New Decision',
        status: 'active',
        decision_text: 'Some decision text',
        rationale: 'Good reasons',
      });
    });
    expect(onSuccess).toHaveBeenCalled();
  });

  it('pre-fills from existing decision in edit mode', () => {
    const decision = {
      id: 'd1',
      title: 'Existing',
      status: 'draft',
      decision_text: 'Text here',
      rationale: 'Because',
    };
    render(
      <DecisionForm projectId="p1" decision={decision} onSuccess={vi.fn()} onCancel={vi.fn()} />,
    );

    expect(screen.getByDisplayValue('Existing')).toBeInTheDocument();
    expect(screen.getByText('draft')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Text here')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Because')).toBeInTheDocument();
    expect(screen.getByText('Update')).toBeInTheDocument();
  });

  it('calls updateDecision in edit mode', async () => {
    const decision = { id: 'd1', title: 'Old', status: 'active', decision_text: '', rationale: '' };
    const onSuccess = vi.fn();
    render(
      <DecisionForm projectId="p1" decision={decision} onSuccess={onSuccess} onCancel={vi.fn()} />,
    );

    fireEvent.change(screen.getByDisplayValue('Old'), {
      target: { value: 'Updated' },
    });
    fireEvent.click(screen.getByText('Update'));

    await waitFor(() => {
      expect(api.updateDecision).toHaveBeenCalledWith('p1', 'd1', expect.objectContaining({
        title: 'Updated',
      }));
    });
  });

  it('cancel calls onCancel', () => {
    const onCancel = vi.fn();
    render(
      <DecisionForm projectId="p1" decision={null} onSuccess={vi.fn()} onCancel={onCancel} />,
    );
    fireEvent.click(screen.getByText('Cancel'));
    expect(onCancel).toHaveBeenCalled();
  });
});
