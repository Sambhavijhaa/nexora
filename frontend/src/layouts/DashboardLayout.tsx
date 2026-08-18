import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Activity, BarChart3, Bell, CheckSquare, FolderKanban, LayoutDashboard, LogOut, Settings, Users } from "lucide-react";

const navigation = [
  { name: "Overview", path: "/dashboard", icon: LayoutDashboard },
  { name: "Projects", path: "/projects", icon: FolderKanban },
  { name: "Tasks", path: "/tasks", icon: CheckSquare },
  { name: "Team", path: "/team", icon: Users },
  { name: "Analytics", path: "/analytics", icon: BarChart3 },
  { name: "Activity", path: "/activity", icon: Activity },
];

type StoredUser = { name?: string; role?: string; email?: string };

function readUser(): StoredUser {
  try { return JSON.parse(localStorage.getItem("nexora_user") || "{}") as StoredUser; } catch { return {}; }
}

function initials(name: string) {
  return (name || "N").trim().split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase();
}

export default function DashboardLayout() {
  const navigate = useNavigate();
  const user = readUser();
  const userInitials = initials(user.name || "Nexora");

  function logout() {
    ["nexora_access_token", "nexora_refresh_token", "nexora_token", "nexora_user"].forEach((key) => localStorage.removeItem(key));
    navigate("/login", { replace: true });
  }

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand" aria-label="Nexora">
          <div className="brand-mark" aria-hidden="true">N</div>
          <span>Nexora</span>
        </div>

        <nav className="sidebar-nav">
          <p className="nav-label">Workspace</p>
          {navigation.map(({ name, path, icon: Icon }) => (
            <NavLink key={path} to={path} title={name} className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
              <Icon size={17} aria-hidden="true" />
              <span>{name}</span>
            </NavLink>
          ))}

          <p className="nav-label settings-label">Account</p>
          <NavLink to="/settings" title="Settings" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
            <Settings size={17} aria-hidden="true" />
            <span>Settings</span>
          </NavLink>
          <button className="nav-item logout-nav" onClick={logout} type="button" title="Sign out">
            <LogOut size={17} aria-hidden="true" />
            <span>Sign out</span>
          </button>
        </nav>

        <div className="sidebar-user" aria-label="Signed in user">
          <div className="avatar" aria-hidden="true">{userInitials}</div>
          <div className="user-copy">
            <strong>{user.name || "User"}</strong>
            <span>{user.role || "Member"}</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="topbar-search" role="search" aria-label="Search">
            <span aria-hidden="true">⌕</span>
            <span>Search projects, tasks, people...</span>
            <kbd>Ctrl K</kbd>
          </div>
          <div className="topbar-actions">
            <button className="icon-button" aria-label="View activity" onClick={() => navigate("/activity")} type="button">
              <Bell size={17} aria-hidden="true" />
              <span className="notification-dot" aria-hidden="true" />
            </button>
            <button className="top-avatar" onClick={() => navigate("/settings")} aria-label="Open account settings" type="button">
              {userInitials}
            </button>
          </div>
        </header>
        <section className="page-content"><Outlet /></section>
      </main>
    </div>
  );
}
