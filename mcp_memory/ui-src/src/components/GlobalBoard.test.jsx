import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import GlobalBoard from './GlobalBoard';

const mockProjects = [
  { id: 'p1', name: 'alpha' },
  { id: 'p2', name: 'beta' },
];

const mockTasks = [
  { id: 't1', title: 'Task One', status: 'open', project_id: 'p1', project_name: 'alpha' },
  { id: 't2', title: 'Task Two', status: 'in_progress', project_id: 'p2', project_name: 'beta' },
];

vi.mock('../api', () => ({
  getProjects: vi.fn(() => Promise.resolve([])),
  getAllTasks: vi.fn(() => Promise.resolve([])),
}));

import * as api from '../api';

function renderBoard() {
  return render(
    <MemoryRouter>
      <GlobalBoard />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  api.getProjects.mockResolvedValue([]);
  api.getAllTasks.mockResolvedValue([]);
});

describe('GlobalBoard', () => {
  it('renders without crashing with empty data', async () => {
    renderBoard();
    await waitFor(() => {
      expect(screen.getByTestId('global-board')).toBeInTheDocument();
    });
  });

  it('shows all four kanban columns', async () => {
    renderBoard();
    await waitFor(() => {
      expect(screen.getByTestId('kanban-column-open')).toBeInTheDocument();
      expect(screen.getByTestId('kanban-column-in_progress')).toBeInTheDocument();
      expect(screen.getByTestId('kanban-column-blocked')).toBeInTheDocument();
      expect(screen.getByTestId('kanban-column-done')).toBeInTheDocument();
    });
  });

  it('renders ProjectFilterBar when projects exist', async () => {
    api.getProjects.mockResolvedValue(mockProjects);
    api.getAllTasks.mockResolvedValue(mockTasks);

    renderBoard();

    await waitFor(() => {
      expect(screen.getByTestId('project-filter-bar')).toBeInTheDocument();
    });
  });

  it('does not render ProjectFilterBar when no projects', async () => {
    api.getProjects.mockResolvedValue([]);
    api.getAllTasks.mockResolvedValue([]);

    renderBoard();

    await waitFor(() => {
      expect(screen.getByTestId('global-board')).toBeInTheDocument();
    });

    expect(screen.queryByTestId('project-filter-bar')).not.toBeInTheDocument();
  });
});
