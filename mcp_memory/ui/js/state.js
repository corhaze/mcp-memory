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
    showAddSubtaskForm: new Set(), // Track which tasks have the add-subtask form open
    taskNotes: {},
    globalNotes: [],
    expandedGlobalNotes: new Set(),
    globalNoteFilter: '',
    searchResults: null,
    searchMode: 'current', // 'current' | 'all'
};
