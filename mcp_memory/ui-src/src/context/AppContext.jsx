import { createContext, useContext, useReducer } from 'react';

const AppStateContext = createContext(null);
const AppDispatchContext = createContext(null);

function toggleInSet(set, value) {
  const next = new Set(set);
  if (next.has(value)) {
    next.delete(value);
  } else {
    next.add(value);
  }
  return next;
}

export const initialState = {
  expandedTasks: new Set(),
  expandedNotes: new Set(),
  expandedGlobalNotes: new Set(),
  expandedSubtasks: new Set(),
  showAddTaskForm: false,
  showAddNoteForm: false,
  showAddGlobalNoteForm: false,
  showAddSubtaskForm: new Set(),
  showAddTaskNoteForm: new Set(),
  editingTaskId: null,
  editingNoteId: null,
  taskFilter: '',
  decisionFilter: '',
  noteFilter: '',
  globalNoteFilter: '',
};

export function appReducer(state, action) {
  switch (action.type) {
    case 'TOGGLE_TASK_EXPANDED':
      return { ...state, expandedTasks: toggleInSet(state.expandedTasks, action.id) };
    case 'TOGGLE_NOTE_EXPANDED':
      return { ...state, expandedNotes: toggleInSet(state.expandedNotes, action.id) };
    case 'TOGGLE_GLOBAL_NOTE_EXPANDED':
      return { ...state, expandedGlobalNotes: toggleInSet(state.expandedGlobalNotes, action.id) };
    case 'TOGGLE_SUBTASK_EXPANDED':
      return { ...state, expandedSubtasks: toggleInSet(state.expandedSubtasks, action.id) };
    case 'TOGGLE_ADD_SUBTASK_FORM':
      return { ...state, showAddSubtaskForm: toggleInSet(state.showAddSubtaskForm, action.id) };
    case 'TOGGLE_ADD_TASK_NOTE_FORM':
      return { ...state, showAddTaskNoteForm: toggleInSet(state.showAddTaskNoteForm, action.id) };
    case 'SET_SHOW_ADD_TASK_FORM':
      return { ...state, showAddTaskForm: action.value };
    case 'SET_SHOW_ADD_NOTE_FORM':
      return { ...state, showAddNoteForm: action.value };
    case 'SET_SHOW_ADD_GLOBAL_NOTE_FORM':
      return { ...state, showAddGlobalNoteForm: action.value };
    case 'SET_EDITING_TASK':
      return { ...state, editingTaskId: action.id };
    case 'SET_EDITING_NOTE':
      return { ...state, editingNoteId: action.id };
    case 'SET_TASK_FILTER':
      return { ...state, taskFilter: action.value };
    case 'SET_DECISION_FILTER':
      return { ...state, decisionFilter: action.value };
    case 'SET_NOTE_FILTER':
      return { ...state, noteFilter: action.value };
    case 'SET_GLOBAL_NOTE_FILTER':
      return { ...state, globalNoteFilter: action.value };
    case 'RESET_FORMS':
      return {
        ...state,
        showAddTaskForm: false,
        showAddNoteForm: false,
        showAddGlobalNoteForm: false,
        showAddSubtaskForm: new Set(),
        showAddTaskNoteForm: new Set(),
        editingTaskId: null,
        editingNoteId: null,
      };
    default:
      return state;
  }
}

export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(appReducer, initialState);
  return (
    <AppStateContext.Provider value={state}>
      <AppDispatchContext.Provider value={dispatch}>
        {children}
      </AppDispatchContext.Provider>
    </AppStateContext.Provider>
  );
}

export function useAppState() {
  const context = useContext(AppStateContext);
  if (context === null) {
    throw new Error('useAppState must be used within an AppProvider');
  }
  return context;
}

export function useAppDispatch() {
  const context = useContext(AppDispatchContext);
  if (context === null) {
    throw new Error('useAppDispatch must be used within an AppProvider');
  }
  return context;
}
