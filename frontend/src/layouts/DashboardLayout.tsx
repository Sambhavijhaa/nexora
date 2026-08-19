import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Bell, LogOut } from "lucide-react";

const navigation = [
  { name: "Dashboard", path: "/dashboard" },
  { name: "Projects", path: "/projects" },
  { name: "Tasks", path: "/tasks" },
  { name: "Team", path: "/team" },
  { name: "Analytics", path: "/analytics" },
  { name: "Activity", path: "/activity" },
];

type StoredUser = { name?: string; role?: string; email?: string };
function readUser(): StoredUser { try { return JSON.parse(localStorage.getItem("nexora_user") || "{}"); } catch { return {}; } }
function initials(name: string) { return (name || "N").trim().split(/\s+/).map((p) => p[0]).join("").slice(0, 2).toUpperCase(); }

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
        <div className="brand"><div className="brand-mark">N</div><span>Nexora</span></div>
        <nav className="sidebar-nav">
          <p className="nav-label">Workspace</p>
          {navigation.map(({ name, path }) => <NavLink key={path} to={path} className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}><span>{name}</span></NavLink>)}
          <p className="nav-label settings-label">Account</p>
          <NavLink to="/notifications" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}><span>Notifications</span></NavLink>
          <NavLink to="/settings" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}><span>Settings</span></NavLink>
          <button className="nav-item logout-nav" onClick={logout} type="button"><span>Sign out</span></button>
        </nav>
        <div className="sidebar-user"><div className="avatar">{userInitials}</div><div className="user-copy"><strong>{user.name || "User"}</strong><span>{user.role || "Member"}</span></div></div>
      </aside>
      <main className="main-content">
        <header className="topbar">
          <div className="topbar-spacer" />
          <div className="topbar-actions">
            <button className="icon-button" aria-label="Notifications" onClick={() => navigate("/notifications")} type="button"><Bell size={17}/></button>
            <button className="top-avatar" onClick={() => navigate("/settings")} aria-label="Account settings" type="button">{userInitials}</button>
          </div>
        </header>
        <section className="page-content"><Outlet /></section>
      </main>
    </div>
  );
}
