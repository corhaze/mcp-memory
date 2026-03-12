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
    editingTaskId: null,           // ID of the task currently showing its inline edit form
    editingNoteId: null,           // ID of the project note currently showing its inline edit form
    showAddTaskForm: false,        // Whether the top-level "add task" inline form is visible
    showAddNoteForm: false,        // Whether the inline "add note" form is visible
    showAddGlobalNoteForm: false,  // Whether the inline "add global note" form is visible
    showAddTaskNoteForm: new Set(), // Track which tasks have the add-note inline form open
    taskNotes: {},
    activeTaskId: null,          // task ID currently shown in the task detail view
    activeNoteId: null,          // note ID currently shown in the note detail view
    expandedSubtasks: new Set(), // subtask IDs expanded in the task detail view
    subtaskDetails: {},          // taskId → fetched detail object (cache)
    globalNotes: [],
    expandedNotes: new Set(),
    expandedGlobalNotes: new Set(),
    globalNoteFilter: '',
    searchResults: null,
    lastFetchedAt: null,   // timestamp of last successful project data fetch
    hiddenAt: null,        // timestamp when browser tab was hidden
};
