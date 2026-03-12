import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppProvider } from './src/context/AppContext';

function EmptyState() {
  return <div data-testid="empty-state">EmptyState</div>;
}

function GlobalWorkspace() {
  return <div data-testid="global-workspace">GlobalWorkspace</div>;
}

function NoteDetail() {
  return <div data-testid="note-detail">NoteDetail</div>;
}

function ProjectView() {
  return <div data-testid="project-view">ProjectView</div>;
}

function TaskDetail() {
  return <div data-testid="task-detail">TaskDetail</div>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<EmptyState />} />
      <Route path="/global" element={<GlobalWorkspace />} />
      <Route path="/global/notes/:noteId" element={<NoteDetail />} />
      <Route path="/:projectName" element={<ProjectView />} />
      <Route path="/:projectName/:tab" element={<ProjectView />} />
      <Route path="/:projectName/tasks/:taskId" element={<TaskDetail />} />
      <Route path="/:projectName/notes/:noteId" element={<NoteDetail />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppProvider>
        <AppRoutes />
      </AppProvider>
    </BrowserRouter>
  );
}

// Exported for testing with MemoryRouter
export { AppRoutes };
