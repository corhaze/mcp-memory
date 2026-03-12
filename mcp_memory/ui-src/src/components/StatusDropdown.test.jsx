import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import StatusDropdown from './StatusDropdown';

describe('StatusDropdown', () => {
  it('renders current status', () => {
    render(<StatusDropdown currentStatus="open" onStatusChange={vi.fn()} />);
    expect(screen.getByRole('button', { name: /open/ })).toBeInTheDocument();
  });

  it('click opens options', async () => {
    const user = userEvent.setup();
    render(<StatusDropdown currentStatus="open" onStatusChange={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: /open/ }));

    const options = screen.getAllByRole('button').filter((b) => b.classList.contains('status-option'));
    expect(options).toHaveLength(5);
  });

  it('selecting option calls onStatusChange', async () => {
    const user = userEvent.setup();
    const onStatusChange = vi.fn();
    render(<StatusDropdown currentStatus="open" onStatusChange={onStatusChange} />);

    await user.click(screen.getByRole('button', { name: /open/ }));
    const doneOption = screen.getAllByRole('button').find(
      (b) => b.classList.contains('status-option') && b.textContent.includes('done')
    );
    await user.click(doneOption);

    expect(onStatusChange).toHaveBeenCalledWith('done');
  });

  it('options include all 5 statuses', async () => {
    const user = userEvent.setup();
    render(<StatusDropdown currentStatus="open" onStatusChange={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: /open/ }));

    const options = screen.getAllByRole('button').filter((b) => b.classList.contains('status-option'));
    const labels = options.map((o) => o.textContent);
    expect(labels.some((l) => l.includes('open'))).toBe(true);
    expect(labels.some((l) => l.includes('in_progress'))).toBe(true);
    expect(labels.some((l) => l.includes('blocked'))).toBe(true);
    expect(labels.some((l) => l.includes('done'))).toBe(true);
    expect(labels.some((l) => l.includes('cancelled'))).toBe(true);
  });
});
