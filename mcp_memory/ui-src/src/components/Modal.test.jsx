import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Modal from './Modal';

describe('Modal', () => {
  it('hidden when isOpen is false', () => {
    render(<Modal isOpen={false} onClose={vi.fn()} title="Test">Content</Modal>);
    expect(screen.queryByTestId('modal-overlay')).not.toBeInTheDocument();
  });

  it('visible when isOpen is true', () => {
    render(<Modal isOpen={true} onClose={vi.fn()} title="Test">Content</Modal>);
    expect(screen.getByTestId('modal-overlay')).toBeInTheDocument();
    expect(screen.getByText('Test')).toBeInTheDocument();
  });

  it('renders children', () => {
    render(<Modal isOpen={true} onClose={vi.fn()} title="T"><p>Hello</p></Modal>);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });

  it('close button calls onClose', () => {
    const onClose = vi.fn();
    render(<Modal isOpen={true} onClose={onClose} title="T">X</Modal>);
    fireEvent.click(screen.getByLabelText('Close'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('Escape key calls onClose', () => {
    const onClose = vi.fn();
    render(<Modal isOpen={true} onClose={onClose} title="T">X</Modal>);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('overlay click calls onClose', () => {
    const onClose = vi.fn();
    render(<Modal isOpen={true} onClose={onClose} title="T">X</Modal>);
    fireEvent.click(screen.getByTestId('modal-overlay'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
