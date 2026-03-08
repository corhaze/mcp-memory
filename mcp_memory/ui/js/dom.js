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
    decisionListEl: $('decision-list'),
    noteListEl: $('note-list'),
    timelineListEl: $('timeline-list'),
    globalNoteListEl: $('global-note-list'),
    searchInput: $('global-search-input'),
    searchTab: $('tab-search'),
    clearSearchBtn: $('clear-search-btn'),
    searchTasksList: $('search-tasks-list'),
    searchDecisionsList: $('search-decisions-list'),
    searchNotesList: $('search-notes-list'),
    searchEmptyState: $('search-empty-state'),

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
    taskFilters: $('task-filters'),
    decisionFilters: $('decision-filters'),
    noteFilters: $('note-filters'),
};

// Re-export $ for convenience in other modules
export default $;
