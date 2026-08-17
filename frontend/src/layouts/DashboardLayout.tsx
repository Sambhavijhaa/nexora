import { NavLink, Outlet } from "react-router-dom";
import {
  BarChart3,
  CheckSquare,
  FolderKanban,
  LayoutDashboard,
  Settings,
  Users,
  Bell,
  Search,
} from "lucide-react";

const navigation = [
  { name: "Dashboard", path: "/dashboard", icon: LayoutDashboard },
  { name: "Projects", path: "/projects", icon: FolderKanban },
  { name: "Tasks", path: "/tasks", icon: CheckSquare },
  { name: "Team", path: "/team", icon: Users },
  { name: "Analytics", path: "/analytics", icon: BarChart3 },
];

export default function DashboardLayout() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">N</div>
          <span>Nexora</span>
        </div>

        <nav className="sidebar-nav">
          <p className="nav-label">Workspace</p>
          {navigation.map(({ name, path, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
            >
              <Icon size={18} />
              <span>{name}</span>
            </NavLink>
          ))}

          <p className="nav-label settings-label">Account</p>
          <NavLink
            to="/settings"
            className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
          >
            <Settings size={18} />
            <span>Settings</span>
          </NavLink>
        </nav>

        <div className="sidebar-user">
          <div className="avatar">SJ</div>
          <div className="user-copy">
            <strong>Sambhavi</strong>
            <span>Administrator</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="topbar-search">
            <Search size={17} />
            <span>Search anything...</span>
            <kbd>⌘ K</kbd>
          </div>
          <div className="topbar-actions">
            <button className="icon-button" aria-label="Notifications">
              <Bell size={18} />
              <span className="notification-dot" />
            </button>
            <div className="top-avatar">SJ</div>
          </div>
        </header>

        <section className="page-content">
          <Outlet />
        </section>
      </main>
    </div>
  );
}
