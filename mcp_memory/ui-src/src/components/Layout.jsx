import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

export default function Layout() {
  return (
    <div id="app">
      <Sidebar />
      <main id="main">
        <Outlet />
      </main>
    </div>
  );
}
