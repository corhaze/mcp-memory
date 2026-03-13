import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ProjectFilterBar from './ProjectFilterBar';

const mockProjects = [
  { id: 'p1', name: 'alpha' },
  { id: 'p2', name: 'beta' },
  { id: 'p3', name: 'gamma' },
];

describe('ProjectFilterBar', () => {
  it('renders one button per project', () => {
    render(
      <ProjectFilterBar
        projects={mockProjects}
        selectedProjectIds={new Set(['p1', 'p2', 'p3'])}
        onToggle={vi.fn()}
      />,
    );
    expect(screen.getByText('alpha')).toBeInTheDocument();
    expect(screen.getByText('beta')).toBeInTheDocument();
    expect(screen.getByText('gamma')).toBeInTheDocument();
  });

  it('applies active class to selected projects', () => {
    render(
      <ProjectFilterBar
        projects={mockProjects}
        selectedProjectIds={new Set(['p1', 'p3'])}
        onToggle={vi.fn()}
      />,
    );
    expect(screen.getByText('alpha').className).toContain('active');
    expect(screen.getByText('beta').className).not.toContain('active');
    expect(screen.getByText('gamma').className).toContain('active');
  });

  it('calls onToggle with project id on click', () => {
    const onToggle = vi.fn();
    render(
      <ProjectFilterBar
        projects={mockProjects}
        selectedProjectIds={new Set(['p1'])}
        onToggle={onToggle}
      />,
    );
    fireEvent.click(screen.getByText('beta'));
    expect(onToggle).toHaveBeenCalledWith('p2');
  });

  it('returns null when projects is empty', () => {
    const { container } = render(
      <ProjectFilterBar
        projects={[]}
        selectedProjectIds={new Set()}
        onToggle={vi.fn()}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('returns null when projects is null', () => {
    const { container } = render(
      <ProjectFilterBar
        projects={null}
        selectedProjectIds={new Set()}
        onToggle={vi.fn()}
      />,
    );
    expect(container.firstChild).toBeNull();
  });
});
