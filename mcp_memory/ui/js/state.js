/* state.js — Central state object */

export const state = {
    projects: [],
    activeProjectId: null,
    tasks: [],
    decisions: [],
    notes: [],
    timeline: [],
    taskFilter: 'open',
    decisionFilter: '',
    noteFilter: '',
    expandedTasks: new Set(),
    taskNotes: {},
    globalNotes: [],
    searchResults: null,
};
