import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import DecisionDetail from './DecisionDetail';

vi.mock('../hooks/useProjects');
vi.mock('../api');

import { useProjects } from '../hooks/useProjects';
import * as api from '../api';

const mockProjects = [{ id: 'p1', name: 'my-project', status: 'active' }];

const mockDecision = {
  id: 'd1',
  title: 'Use SQLite for storage',
  status: 'active',
  decision_text: 'SQLite is the chosen storage backend.',
  rationale: 'Lightweight, no server needed.',
};

beforeEach(() => {
  vi.clearAllMocks();
  useProjects.mockReturnValue({ projects: mockProjects, loading: false, error: null });
});

function renderDecisionDetail(path = '/my-project/decisions/d1') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path=":projectName/decisions/:decisionId" element={<DecisionDetail />} />
        <Route path=":projectName/decisions" element={<div>Decisions list</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('DecisionDetail', () => {
  it('renders loading state initially', () => {
    useProjects.mockReturnValue({ projects: null, loading: true, error: null });
    api.getProjectDecisions.mockResolvedValue({ items: [mockDecision] });

    renderDecisionDetail();

    expect(screen.getByText('Loading decision...')).toBeInTheDocument();
  });

  it('renders decision title and text after load', async () => {
    api.getProjectDecisions.mockResolvedValue({ items: [mockDecision] });

    renderDecisionDetail();

    await waitFor(() => {
      expect(screen.getByTestId('decision-detail')).toBeInTheDocument();
    });

    expect(screen.getByText('Use SQLite for storage')).toBeInTheDocument();
    expect(screen.getByText(/SQLite is the chosen storage backend/)).toBeInTheDocument();
  });

  it('renders rationale when present', async () => {
    api.getProjectDecisions.mockResolvedValue({ items: [mockDecision] });

    renderDecisionDetail();

    await waitFor(() => {
      expect(screen.getByText(/Lightweight, no server needed/)).toBeInTheDocument();
    });
  });

  it('shows error when decision not found', async () => {
    api.getProjectDecisions.mockResolvedValue({ items: [] });

    renderDecisionDetail();

    await waitFor(() => {
      expect(screen.getByText('Error: Decision not found')).toBeInTheDocument();
    });
  });

  it('shows error when API fails', async () => {
    api.getProjectDecisions.mockRejectedValue(new Error('Network error'));

    renderDecisionDetail();

    await waitFor(() => {
      expect(screen.getByText('Error: Network error')).toBeInTheDocument();
    });
  });
});
