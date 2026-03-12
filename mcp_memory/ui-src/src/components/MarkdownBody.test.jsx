import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import MarkdownBody from './MarkdownBody';

describe('MarkdownBody', () => {
  it('renders markdown string as HTML', () => {
    const { container } = render(<MarkdownBody content="**bold text**" />);
    const strong = container.querySelector('strong');
    expect(strong).toBeInTheDocument();
    expect(strong.textContent).toBe('bold text');
  });

  it('renders nothing for null content', () => {
    const { container } = render(<MarkdownBody content={null} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders nothing for empty string', () => {
    const { container } = render(<MarkdownBody content="" />);
    expect(container.innerHTML).toBe('');
  });

  it('applies markdown-body className', () => {
    const { container } = render(<MarkdownBody content="hello" />);
    expect(container.querySelector('.markdown-body')).toBeInTheDocument();
  });

  it('applies extra className', () => {
    const { container } = render(<MarkdownBody content="hello" className="extra" />);
    const el = container.querySelector('.markdown-body');
    expect(el).toHaveClass('extra');
  });
});
