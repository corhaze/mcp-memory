/* dom.js — DOM element references and selection helpers */

export const $ = id => document.getElementById(id);

export const els = {
    projectList: $('project-list'),
    emptyState: $('empty-state'),
    projectView: $('project-view'),
    projectName: $('project-name'),
    projectStatus: $('project-status-badge'),
    projectDesc: $('project-description'),
    projectSummary: $('project-summary-text'),
    taskListEl: $('task-list'),
    addTaskFormContainer: $('add-task-form-container'),
    decisionListEl: $('decision-list'),
    noteListEl: $('note-list'),
    timelineListEl: $('timeline-list'),
    globalView: $('global-view'),
    taskDetailView: $('task-detail-view'),
    taskDetailContent: $('task-detail-content'),
    noteDetailView: $('note-detail-view'),
    noteDetailContent: $('note-detail-content'),
    globalWorkspaceBtn: $('global-workspace-btn'),
    globalNoteListMain: $('global-note-list-main'),
    searchInput: $('global-search-input'),
    searchTab: $('tab-search'),
    clearSearchBtn: $('clear-search-btn'),
    searchResultsList: $('search-results-list'),
    searchEmbeddingsNotice: $('search-embeddings-notice'),
    searchEmptyState: $('search-empty-state'),
    kanbanBoard: $('kanban-board'),

    // Buttons & Inputs
    addProjectBtn: $('add-project-btn'),
    addGlobalNoteBtn: $('add-global-note-btn'),
    editProjectBtn: $('edit-project-btn'),
    deleteProjectBtn: $('delete-project-btn'),
    addTaskBtn: $('add-task-btn'),
    addDecisionBtn: $('add-decision-btn'),
    addNoteBtn: $('add-note-btn'),

    // Modal
    modalOverlay: $('modal-overlay'),
    modalTitle: $('modal-title'),
    modalBody: $('modal-body'),
    modalClose: $('modal-close'),
    modalCancel: $('modal-cancel'),
    modalSave: $('modal-save'),

    // Tabs & Filters
    tabBar: document.querySelector('.tab-bar'),
    globalTabBar: $('global-tab-bar'),
    taskFilters: $('task-filters'),
    decisionFilters: $('decision-filters'),
    noteFilters: $('note-filters'),
    globalNoteFilters: $('global-note-filters'),
};

// Re-export $ for convenience in other modules
export default $;
