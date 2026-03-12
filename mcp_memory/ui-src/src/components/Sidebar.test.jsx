import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import Sidebar from './Sidebar';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ projectName: 'alpha' }),
  };
});

vi.mock('../hooks/useProjects');

import { useProjects } from '../hooks/useProjects';

beforeEach(() => {
  vi.clearAllMocks();
});

function renderSidebar() {
  return render(
    <MemoryRouter>
      <Sidebar />
    </MemoryRouter>,
  );
}

describe('Sidebar', () => {
  it('renders project list from mock data', () => {
    useProjects.mockReturnValue({
      projects: [
        { id: '1', name: 'alpha' },
        { id: '2', name: 'beta' },
      ],
      loading: false,
      error: null,
      refresh: vi.fn(),
    });

    renderSidebar();
    expect(screen.getByText('alpha')).toBeInTheDocument();
    expect(screen.getByText('beta')).toBeInTheDocument();
  });

  it('clicking a project navigates', async () => {
    const user = userEvent.setup();
    useProjects.mockReturnValue({
      projects: [{ id: '1', name: 'alpha' }, { id: '2', name: 'beta' }],
      loading: false,
      error: null,
      refresh: vi.fn(),
    });

    renderSidebar();
    await user.click(screen.getByText('beta'));
    expect(mockNavigate).toHaveBeenCalledWith('/beta');
  });

  it('active project has active class', () => {
    useProjects.mockReturnValue({
      projects: [
        { id: '1', name: 'alpha' },
        { id: '2', name: 'beta' },
      ],
      loading: false,
      error: null,
      refresh: vi.fn(),
    });

    renderSidebar();
    const alphaBtn = screen.getByText('alpha').closest('button');
    const betaBtn = screen.getByText('beta').closest('button');
    expect(alphaBtn).toHaveClass('active');
    expect(betaBtn).not.toHaveClass('active');
  });

  it('Global Workspace button is present', () => {
    useProjects.mockReturnValue({
      projects: [],
      loading: false,
      error: null,
      refresh: vi.fn(),
    });

    renderSidebar();
    expect(screen.getByText('// global workspace')).toBeInTheDocument();
  });

  it('clicking Global Workspace navigates', async () => {
    const user = userEvent.setup();
    useProjects.mockReturnValue({
      projects: [],
      loading: false,
      error: null,
      refresh: vi.fn(),
    });

    renderSidebar();
    await user.click(screen.getByText('// global workspace'));
    expect(mockNavigate).toHaveBeenCalledWith('/global');
  });

  it('loading state shows when loading', () => {
    useProjects.mockReturnValue({
      projects: null,
      loading: true,
      error: null,
      refresh: vi.fn(),
    });

    renderSidebar();
    expect(screen.getByText('Loading projects...')).toBeInTheDocument();
  });

  it('search input is present', () => {
    useProjects.mockReturnValue({
      projects: [],
      loading: false,
      error: null,
      refresh: vi.fn(),
    });

    renderSidebar();
    expect(screen.getByPlaceholderText('Search all projects...')).toBeInTheDocument();
  });
});
