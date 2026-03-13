import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useProjects } from './useProjects';
import * as api from '../api';

vi.mock('../api');

beforeEach(() => {
  vi.restoreAllMocks();
});

describe('useProjects', () => {
  it('transitions from loading to data loaded', async () => {
    const projects = [{ id: '1', name: 'alpha' }];
    api.getProjects.mockResolvedValue(projects);

    const { result } = renderHook(() => useProjects());

    // Initially loading
    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.projects).toEqual(projects);
    expect(result.current.error).toBeNull();
  });

  it('sets error state when API throws', async () => {
    api.getProjects.mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useProjects());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe('Network error');
    expect(result.current.projects).toBeNull();
  });

  it('refresh re-fetches data', async () => {
    const first = [{ id: '1' }];
    const second = [{ id: '1' }, { id: '2' }];
    api.getProjects.mockResolvedValueOnce(first).mockResolvedValueOnce(second);

    const { result } = renderHook(() => useProjects());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.projects).toEqual(first);

    await act(() => result.current.refresh());

    expect(result.current.projects).toEqual(second);
    expect(api.getProjects).toHaveBeenCalledTimes(2);
  });
});
