import { describe, it, expect } from 'vitest';
import { appReducer, initialState } from './AppContext';

describe('appReducer', () => {
  it('TOGGLE_TASK_EXPANDED adds to set', () => {
    const next = appReducer(initialState, { type: 'TOGGLE_TASK_EXPANDED', id: 't1' });
    expect(next.expandedTasks.has('t1')).toBe(true);
  });

  it('TOGGLE_TASK_EXPANDED removes from set on second toggle', () => {
    const first = appReducer(initialState, { type: 'TOGGLE_TASK_EXPANDED', id: 't1' });
    const second = appReducer(first, { type: 'TOGGLE_TASK_EXPANDED', id: 't1' });
    expect(second.expandedTasks.has('t1')).toBe(false);
  });

  it('TOGGLE_NOTE_EXPANDED works', () => {
    const next = appReducer(initialState, { type: 'TOGGLE_NOTE_EXPANDED', id: 'n1' });
    expect(next.expandedNotes.has('n1')).toBe(true);
  });

  it('TOGGLE_GLOBAL_NOTE_EXPANDED works', () => {
    const next = appReducer(initialState, { type: 'TOGGLE_GLOBAL_NOTE_EXPANDED', id: 'gn1' });
    expect(next.expandedGlobalNotes.has('gn1')).toBe(true);
  });

  it('TOGGLE_SUBTASK_EXPANDED works', () => {
    const next = appReducer(initialState, { type: 'TOGGLE_SUBTASK_EXPANDED', id: 'st1' });
    expect(next.expandedSubtasks.has('st1')).toBe(true);
  });

  it('TOGGLE_ADD_SUBTASK_FORM works', () => {
    const next = appReducer(initialState, { type: 'TOGGLE_ADD_SUBTASK_FORM', id: 't1' });
    expect(next.showAddSubtaskForm.has('t1')).toBe(true);
  });

  it('TOGGLE_ADD_TASK_NOTE_FORM works', () => {
    const next = appReducer(initialState, { type: 'TOGGLE_ADD_TASK_NOTE_FORM', id: 't1' });
    expect(next.showAddTaskNoteForm.has('t1')).toBe(true);
  });

  it('SET_SHOW_ADD_TASK_FORM sets value', () => {
    const next = appReducer(initialState, { type: 'SET_SHOW_ADD_TASK_FORM', value: true });
    expect(next.showAddTaskForm).toBe(true);
  });

  it('SET_SHOW_ADD_NOTE_FORM sets value', () => {
    const next = appReducer(initialState, { type: 'SET_SHOW_ADD_NOTE_FORM', value: true });
    expect(next.showAddNoteForm).toBe(true);
  });

  it('SET_SHOW_ADD_GLOBAL_NOTE_FORM sets value', () => {
    const next = appReducer(initialState, { type: 'SET_SHOW_ADD_GLOBAL_NOTE_FORM', value: true });
    expect(next.showAddGlobalNoteForm).toBe(true);
  });

  it('SET_TASK_FILTER updates value', () => {
    const next = appReducer(initialState, { type: 'SET_TASK_FILTER', value: 'open' });
    expect(next.taskFilter).toBe('open');
  });

  it('SET_DECISION_FILTER updates value', () => {
    const next = appReducer(initialState, { type: 'SET_DECISION_FILTER', value: 'active' });
    expect(next.decisionFilter).toBe('active');
  });

  it('SET_NOTE_FILTER updates value', () => {
    const next = appReducer(initialState, { type: 'SET_NOTE_FILTER', value: 'search' });
    expect(next.noteFilter).toBe('search');
  });

  it('SET_GLOBAL_NOTE_FILTER updates value', () => {
    const next = appReducer(initialState, { type: 'SET_GLOBAL_NOTE_FILTER', value: 'test' });
    expect(next.globalNoteFilter).toBe('test');
  });

  it('SET_EDITING_TASK sets and clears', () => {
    const set = appReducer(initialState, { type: 'SET_EDITING_TASK', id: 't1' });
    expect(set.editingTaskId).toBe('t1');
    const cleared = appReducer(set, { type: 'SET_EDITING_TASK', id: null });
    expect(cleared.editingTaskId).toBeNull();
  });

  it('SET_EDITING_NOTE sets and clears', () => {
    const set = appReducer(initialState, { type: 'SET_EDITING_NOTE', id: 'n1' });
    expect(set.editingNoteId).toBe('n1');
    const cleared = appReducer(set, { type: 'SET_EDITING_NOTE', id: null });
    expect(cleared.editingNoteId).toBeNull();
  });

  it('RESET_FORMS resets all form state', () => {
    let state = appReducer(initialState, { type: 'SET_SHOW_ADD_TASK_FORM', value: true });
    state = appReducer(state, { type: 'SET_EDITING_TASK', id: 't1' });
    state = appReducer(state, { type: 'TOGGLE_ADD_SUBTASK_FORM', id: 't1' });
    const reset = appReducer(state, { type: 'RESET_FORMS' });
    expect(reset.showAddTaskForm).toBe(false);
    expect(reset.showAddNoteForm).toBe(false);
    expect(reset.showAddGlobalNoteForm).toBe(false);
    expect(reset.showAddSubtaskForm.size).toBe(0);
    expect(reset.showAddTaskNoteForm.size).toBe(0);
    expect(reset.editingTaskId).toBeNull();
    expect(reset.editingNoteId).toBeNull();
  });

  it('unknown action returns state unchanged', () => {
    const next = appReducer(initialState, { type: 'UNKNOWN' });
    expect(next).toBe(initialState);
  });
});
