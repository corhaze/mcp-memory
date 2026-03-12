import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import StatusBadge from './StatusBadge';

describe('StatusBadge', () => {
  it('renders status text', () => {
    render(<StatusBadge status="open" />);
    expect(screen.getByText(/open/)).toBeInTheDocument();
  });

  it('renders status emoji', () => {
    render(<StatusBadge status="done" />);
    // done emoji is checkmark
    expect(screen.getByText(/\u2713/)).toBeInTheDocument();
  });

  it('applies correct badge class', () => {
    const { container } = render(<StatusBadge status="blocked" />);
    const badge = container.querySelector('.status-badge');
    expect(badge).toHaveClass('badge-blocked');
  });

  it('applies badge-in_progress class for in_progress status', () => {
    const { container } = render(<StatusBadge status="in_progress" />);
    const badge = container.querySelector('.status-badge');
    expect(badge).toHaveClass('badge-in_progress');
  });
});
