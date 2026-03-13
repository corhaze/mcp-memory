import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import EmptyState from './EmptyState';

describe('EmptyState', () => {
  it('renders placeholder text', () => {
    render(<EmptyState />);
    expect(screen.getByText('Select a project')).toBeInTheDocument();
    expect(screen.getByText(/Choose a project/)).toBeInTheDocument();
  });

  it('has empty-state class', () => {
    render(<EmptyState />);
    expect(screen.getByTestId('empty-state')).toHaveClass('empty-state');
  });
});
