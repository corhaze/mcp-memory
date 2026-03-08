/* state.js — Central state object */

export const state = {
    activeView: 'empty', // 'empty' | 'project' | 'global'
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
    expandedGlobalNotes: new Set(),
    globalNoteFilter: '',
    searchResults: null,
};
