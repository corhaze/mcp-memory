import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AppProvider } from '../context/AppContext';
import ProjectView from './ProjectView';

vi.mock('../hooks/useProjects');
vi.mock('../hooks/useProjectData');

import { useProjects } from '../hooks/useProjects';
import { useProjectData } from '../hooks/useProjectData';

beforeEach(() => {
  vi.clearAllMocks();
});

function renderProjectView(path = '/my-project') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppProvider>
        <Routes>
          <Route path=":projectName" element={<ProjectView />} />
          <Route path=":projectName/:tab" element={<ProjectView />} />
        </Routes>
      </AppProvider>
    </MemoryRouter>,
  );
}

const mockProject = {
  id: 'p1',
  name: 'my-project',
  status: 'active',
  description: 'Test project description',
};

describe('ProjectView', () => {
  it('renders tab bar with all tabs', () => {
    useProjects.mockReturnValue({
      projects: [mockProject],
      loading: false,
      error: null,
      refresh: vi.fn(),
    });
    useProjectData.mockReturnValue({
      loading: false,
      error: null,
      tasks: [],
      decisions: [],
      notes: [],
      timeline: [],
      summary: null,
      refresh: vi.fn(),
    });

    renderProjectView();
    expect(screen.getByText('Summary')).toBeInTheDocument();
    expect(screen.getByText('Tasks')).toBeInTheDocument();
    expect(screen.getByText('Board')).toBeInTheDocument();
    expect(screen.getByText('Decisions')).toBeInTheDocument();
    expect(screen.getByText('Notes')).toBeInTheDocument();
    expect(screen.getByText('Timeline')).toBeInTheDocument();
  });

  it('active tab from URL params', () => {
    useProjects.mockReturnValue({
      projects: [mockProject],
      loading: false,
      error: null,
      refresh: vi.fn(),
    });
    useProjectData.mockReturnValue({
      loading: false,
      error: null,
      tasks: [],
      decisions: [],
      notes: [],
      timeline: [],
      summary: null,
      refresh: vi.fn(),
    });

    renderProjectView('/my-project/tasks');
    const tasksBtn = screen.getByText('Tasks');
    expect(tasksBtn).toHaveClass('active');
    expect(screen.getByText('Summary')).not.toHaveClass('active');
  });

  it('header shows project name', () => {
    useProjects.mockReturnValue({
      projects: [mockProject],
      loading: false,
      error: null,
      refresh: vi.fn(),
    });
    useProjectData.mockReturnValue({
      loading: false,
      error: null,
      tasks: [],
      decisions: [],
      notes: [],
      timeline: [],
      summary: null,
      refresh: vi.fn(),
    });

    renderProjectView();
    expect(screen.getByText('my-project')).toBeInTheDocument();
  });

  it('loading state while data fetches', () => {
    useProjects.mockReturnValue({
      projects: [mockProject],
      loading: false,
      error: null,
      refresh: vi.fn(),
    });
    useProjectData.mockReturnValue({
      loading: true,
      error: null,
      tasks: null,
      decisions: null,
      notes: null,
      timeline: null,
      summary: null,
      refresh: vi.fn(),
    });

    renderProjectView();
    // Should show loading in the panel area (not the project-level loading)
    const loadingTexts = screen.getAllByText('Loading...');
    expect(loadingTexts.length).toBeGreaterThan(0);
  });
});
