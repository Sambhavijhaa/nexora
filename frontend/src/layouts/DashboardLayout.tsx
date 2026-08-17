import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { BarChart3, Bell, CheckSquare, FolderKanban, LayoutDashboard, LogOut, Settings, Users, Activity } from "lucide-react";

const navigation = [
  { name: "Overview", path: "/dashboard", icon: LayoutDashboard },
  { name: "Projects", path: "/projects", icon: FolderKanban },
  { name: "Tasks", path: "/tasks", icon: CheckSquare },
  { name: "Team", path: "/team", icon: Users },
  { name: "Analytics", path: "/analytics", icon: BarChart3 },
  { name: "Activity", path: "/activity", icon: Activity },
];

export default function DashboardLayout() {
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem("nexora_user") || "{}") as { name?: string; role?: string };
  const initials = (user.name || "N")
    .split(" ")
    .map((part: string) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  function logout() {
    localStorage.removeItem("nexora_access_token");
    localStorage.removeItem("nexora_refresh_token");
    localStorage.removeItem("nexora_token");
    localStorage.removeItem("nexora_user");
    navigate("/login", { replace: true });
  }

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
              <Icon size={17} />
              <span>{name}</span>
            </NavLink>
          ))}

          <p className="nav-label settings-label">Account</p>
          <NavLink
            to="/settings"
            className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
          >
            <Settings size={17} />
            <span>Settings</span>
          </NavLink>
          <button className="nav-item logout-nav" onClick={logout}>
            <LogOut size={17} />
            <span>Sign out</span>
          </button>
        </nav>

        <div className="sidebar-user">
          <div className="avatar">{initials}</div>
          <div className="user-copy">
            <strong>{user.name || "User"}</strong>
            <span>{user.role || "Member"}</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="topbar-search">
            <span>⌕</span>
            <span>Search projects, tasks, people...</span>
            <kbd>⌘ K</kbd>
          </div>
          <div className="topbar-actions">
            <button className="icon-button" aria-label="View activity" onClick={() => navigate("/activity")}>
              <Bell size={17} />
              <span className="notification-dot" />
            </button>
            <button className="top-avatar" onClick={() => navigate("/settings")} aria-label="Open settings">
              {initials}
            </button>
          </div>
        </header>
        <section className="page-content">
          <Outlet />
        </section>
      </main>
    </div>
  );
}
