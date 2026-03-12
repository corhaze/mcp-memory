import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TabBar from './TabBar';

const TABS = [
  { name: 'summary', label: 'Summary' },
  { name: 'tasks', label: 'Tasks' },
  { name: 'notes', label: 'Notes' },
];

describe('TabBar', () => {
  it('renders all tab labels', () => {
    render(<TabBar tabs={TABS} activeTab="summary" onTabClick={() => {}} />);
    expect(screen.getByText('Summary')).toBeInTheDocument();
    expect(screen.getByText('Tasks')).toBeInTheDocument();
    expect(screen.getByText('Notes')).toBeInTheDocument();
  });

  it('active tab has active class', () => {
    render(<TabBar tabs={TABS} activeTab="tasks" onTabClick={() => {}} />);
    const tasksBtn = screen.getByText('Tasks');
    expect(tasksBtn).toHaveClass('active');
    expect(screen.getByText('Summary')).not.toHaveClass('active');
  });

  it('click calls onTabClick with tab name', async () => {
    const user = userEvent.setup();
    const onTabClick = vi.fn();
    render(<TabBar tabs={TABS} activeTab="summary" onTabClick={onTabClick} />);

    await user.click(screen.getByText('Notes'));
    expect(onTabClick).toHaveBeenCalledWith('notes');
  });
});
