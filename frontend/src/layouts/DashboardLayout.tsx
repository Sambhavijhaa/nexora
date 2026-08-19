import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Bell } from "lucide-react";

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
      <style>{`
        @media(max-width:700px){
          .app-shell{min-width:0;overflow-x:hidden}
          .sidebar{width:178px;flex:0 0 178px;padding:16px 8px 12px;position:sticky;top:0;height:100svh;overflow-y:auto}
          .brand{padding:2px 8px 22px;font-size:17px;gap:8px}.brand-mark{width:30px;height:30px;border-radius:8px}
          .nav-label{margin-left:8px;margin-right:8px;font-size:9px}.settings-label{margin-top:18px}
          .nav-item{padding:9px 8px;font-size:11px;gap:7px;white-space:nowrap}
          .sidebar-user{padding:12px 5px 2px}.avatar{width:31px;height:31px}.user-copy strong{font-size:10px}.user-copy span{font-size:9px}
          .topbar{height:58px;padding:0 14px}.topbar-actions{gap:7px}.icon-button{width:32px;height:32px}.top-avatar{width:31px;height:31px}
          .page-content{padding:20px 14px 36px;max-width:none}
          .welcome-section,.page-heading{align-items:flex-start;flex-direction:column;gap:14px;margin-bottom:20px}.welcome-section h2,.page-heading h2,.placeholder-page h2{font-size:24px}
          .stats-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.stat-card{padding:13px}.stat-card h3{font-size:21px}.stat-top{margin-bottom:12px}
          .dashboard-grid,.analytics-grid,.settings-grid{grid-template-columns:1fr;gap:12px}.card-grid,.member-grid{grid-template-columns:1fr;gap:10px}.task-columns{grid-template-columns:1fr;gap:10px}
          .panel{padding:15px}.form-row{flex-direction:column}.workspace-input{width:100%;min-width:0}.primary-button{width:100%}
          .chart-bars{height:180px}.project-card{min-height:0}
        }
        @media(max-width:430px){.sidebar{width:156px;flex-basis:156px}.brand span{font-size:15px}.nav-item{font-size:10px;padding:8px 7px}.page-content{padding-left:11px;padding-right:11px}.stats-grid{gap:7px}.stat-card{padding:11px}.stat-card h3{font-size:19px}}
      `}</style>
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
        <header className="topbar"><div className="topbar-spacer" /><div className="topbar-actions"><button className="icon-button" aria-label="Notifications" onClick={() => navigate("/notifications")} type="button"><Bell size={17}/></button><button className="top-avatar" onClick={() => navigate("/settings")} aria-label="Account settings" type="button">{userInitials}</button></div></header>
        <section className="page-content"><Outlet /></section>
      </main>
    </div>
  );
}
