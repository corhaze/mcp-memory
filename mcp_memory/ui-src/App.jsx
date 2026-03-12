import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppProvider } from './src/context/AppContext';
import Layout from './src/components/Layout';
import EmptyState from './src/components/EmptyState';
import ProjectView from './src/components/ProjectView';
import TaskDetail from './src/components/TaskDetail';

function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<EmptyState />} />
        <Route path="global" element={<div data-testid="global-workspace">Global Workspace placeholder</div>} />
        <Route path="global/notes/:noteId" element={<div data-testid="note-detail">Global Note Detail placeholder</div>} />
        <Route path=":projectName" element={<ProjectView />} />
        <Route path=":projectName/:tab" element={<ProjectView />} />
        <Route path=":projectName/tasks/:taskId" element={<TaskDetail />} />
        <Route path=":projectName/notes/:noteId" element={<div data-testid="note-detail">Note Detail placeholder</div>} />
      </Route>
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
