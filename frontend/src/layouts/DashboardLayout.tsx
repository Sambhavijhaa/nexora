import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { BarChart3, CheckSquare, FolderKanban, LayoutDashboard, Settings, Users, Bell, Search, LogOut } from "lucide-react";

const navigation = [
  { name: "Dashboard", path: "/dashboard", icon: LayoutDashboard },
  { name: "Projects", path: "/projects", icon: FolderKanban },
  { name: "Tasks", path: "/tasks", icon: CheckSquare },
  { name: "Team", path: "/team", icon: Users },
  { name: "Analytics", path: "/analytics", icon: BarChart3 },
];

export default function DashboardLayout() {
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem("nexora_user") || "{}") as { name?: string; role?: string };
  const initials = (user.name || "N").split(" ").map((part: string) => part[0]).join("").slice(0, 2).toUpperCase();
  function logout() { localStorage.clear(); navigate("/login", { replace: true }); }

  return <div className="app-shell"><aside className="sidebar"><div className="brand"><div className="brand-mark">N</div><span>Nexora</span></div><nav className="sidebar-nav"><p className="nav-label">Workspace</p>{navigation.map(({ name, path, icon: Icon }) => <NavLink key={path} to={path} className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}><Icon size={18}/><span>{name}</span></NavLink>)}<p className="nav-label settings-label">Account</p><NavLink to="/settings" className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}><Settings size={18}/><span>Settings</span></NavLink><button className="nav-item logout-nav" onClick={logout}><LogOut size={18}/><span>Sign out</span></button></nav><div className="sidebar-user"><div className="avatar">{initials}</div><div className="user-copy"><strong>{user.name || "User"}</strong><span>{user.role || "Member"}</span></div></div></aside><main className="main-content"><header className="topbar"><div className="topbar-search"><Search size={17}/><span>Search anything...</span><kbd>⌘ K</kbd></div><div className="topbar-actions"><button className="icon-button" aria-label="Notifications"><Bell size={18}/><span className="notification-dot"/></button><div className="top-avatar">{initials}</div></div></header><section className="page-content"><Outlet/></section></main></div>;
}
