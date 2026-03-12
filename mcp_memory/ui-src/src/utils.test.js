import { describe, it, expect } from 'vitest';
import { statusEmoji, formatRelativeTime, entityNavTarget, STATUS_OPTIONS } from './utils';

describe('statusEmoji', () => {
  it('returns correct emoji for each status', () => {
    expect(statusEmoji('open')).toBe('\u25CB');
    expect(statusEmoji('in_progress')).toBe('\u25D1');
    expect(statusEmoji('blocked')).toBe('\u2297');
    expect(statusEmoji('done')).toBe('\u2713');
    expect(statusEmoji('cancelled')).toBe('\u2715');
  });

  it('returns default for unknown status', () => {
    expect(statusEmoji('unknown')).toBe('\u25CB');
  });
});

describe('formatRelativeTime', () => {
  it('returns empty string for falsy input', () => {
    expect(formatRelativeTime(null)).toBe('');
    expect(formatRelativeTime('')).toBe('');
  });

  it('returns "just now" for recent timestamps', () => {
    const now = new Date().toISOString();
    expect(formatRelativeTime(now)).toBe('just now');
  });

  it('returns minutes ago', () => {
    const fiveMinAgo = new Date(Date.now() - 5 * 60000).toISOString();
    expect(formatRelativeTime(fiveMinAgo)).toBe('5m ago');
  });

  it('returns hours ago', () => {
    const twoHoursAgo = new Date(Date.now() - 2 * 3600000).toISOString();
    expect(formatRelativeTime(twoHoursAgo)).toBe('2h ago');
  });

  it('returns days ago', () => {
    const threeDaysAgo = new Date(Date.now() - 3 * 86400000).toISOString();
    expect(formatRelativeTime(threeDaysAgo)).toBe('3d ago');
  });
});

describe('entityNavTarget', () => {
  it('returns task target', () => {
    const result = entityNavTarget({
      entity_type: 'task',
      id: 't1',
      project_name: 'proj',
    });
    expect(result).toEqual({
      projectName: 'proj',
      tab: 'tasks',
      anchor: 'task-t1',
    });
  });

  it('returns null for unknown entity type', () => {
    expect(entityNavTarget({ entity_type: 'unknown' })).toBeNull();
  });

  it('returns null projectName for global_note', () => {
    const result = entityNavTarget({ entity_type: 'global_note', id: 'gn1' });
    expect(result.projectName).toBeNull();
  });
});

describe('STATUS_OPTIONS', () => {
  it('contains all valid statuses', () => {
    expect(STATUS_OPTIONS).toEqual(['open', 'in_progress', 'blocked', 'done', 'cancelled']);
  });
});
