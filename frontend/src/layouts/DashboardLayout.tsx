import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Bell, Menu, X } from "lucide-react";
import { useState } from "react";

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
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  function logout() {
    ["nexora_access_token", "nexora_refresh_token", "nexora_token", "nexora_user"].forEach((key) => localStorage.removeItem(key));
    navigate("/login", { replace: true });
  }

  return (
    <div className="app-shell">
      <style>{`
        .mobile-menu-button,.mobile-nav-close,.mobile-nav-overlay{display:none}
        @media(max-width:700px){
          .app-shell{min-width:0;overflow-x:hidden}
          .sidebar{width:280px!important;min-width:280px!important;flex:0 0 280px!important;padding:18px 12px 12px!important;position:fixed!important;left:0;top:0;height:100svh;z-index:1000;overflow-y:auto;transform:translateX(${mobileNavOpen ? "0" : "-105%"});transition:transform .22s ease;box-shadow:8px 0 30px rgba(0,0,0,.18);background:#fff!important;border-right:1px solid #e5e7eb!important;color:#171a21!important}
          .mobile-nav-overlay{display:${mobileNavOpen ? "block" : "none"};position:fixed;inset:0;background:rgba(0,0,0,.42);z-index:999}
          .mobile-nav-close{display:flex;position:absolute;right:12px;top:12px;width:34px;height:34px;align-items:center;justify-content:center;border:0;border-radius:8px;background:transparent;color:#171a21;cursor:pointer}
          .brand{padding:2px 8px 28px!important;font-size:18px!important;gap:8px;color:#171a21!important}.brand-mark{width:40px!important;height:40px!important;border-radius:10px}
          .sidebar-nav{display:flex!important;visibility:visible!important;opacity:1!important;gap:5px!important}
          .nav-label{margin-left:8px;margin-right:8px;font-size:10px;color:#8a8f9b!important}.settings-label{margin-top:20px}
          .nav-item{display:flex!important;visibility:visible!important;opacity:1!important;padding:12px 10px!important;font-size:15px!important;gap:8px;white-space:nowrap;color:#343944!important;background:transparent!important}
          .nav-item:hover{color:#171a21!important;background:#f3f4f7!important}.nav-item.active{color:#4338a8!important;background:#eeecff!important;box-shadow:inset 3px 0 0 #5548c9!important}
          .logout-nav{text-align:left;color:#343944!important}
          .sidebar-user{padding:14px 7px 2px!important;border-top:1px solid #e5e7eb!important}.avatar{width:34px;height:34px;background:#eeecff;color:#5548c9}.user-copy strong{font-size:12px;color:#252936!important}.user-copy span{font-size:10px;color:#737985!important}
          .main-content{min-width:0;width:100%;flex:1}
          .topbar{height:58px;padding:0 12px}.topbar-actions{gap:7px}.icon-button{width:34px;height:34px}.top-avatar{width:32px;height:32px}
          .mobile-menu-button{display:flex;width:34px;height:34px;align-items:center;justify-content:center;border:1px solid #e5e7eb;border-radius:9px;background:#fff;color:#252936;cursor:pointer}
          .topbar-spacer{display:flex;align-items:center;gap:8px}
          .page-content{padding:20px 14px 36px;max-width:none}
          .welcome-section,.page-heading{align-items:flex-start;flex-direction:column;gap:14px;margin-bottom:20px}.welcome-section h2,.page-heading h2,.placeholder-page h2{font-size:24px}
          .stats-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.stat-card{padding:13px}.stat-card h3{font-size:21px}.stat-top{margin-bottom:12px}
          .dashboard-grid,.analytics-grid,.settings-grid{grid-template-columns:1fr;gap:12px}.card-grid,.member-grid{grid-template-columns:1fr;gap:10px}.task-columns{grid-template-columns:1fr;gap:10px}
          .panel{padding:15px}.form-row{flex-direction:column}.workspace-input{width:100%;min-width:0}.primary-button{width:100%}
          .chart-bars{height:180px}.project-card{min-height:0}
        }
        @media(max-width:430px){.sidebar{width:280px!important;min-width:280px!important;flex-basis:280px!important}.brand span{font-size:17px}.nav-item{font-size:14px!important;padding:11px 9px!important}.page-content{padding-left:11px;padding-right:11px}.stats-grid{gap:7px}.stat-card{padding:11px}.stat-card h3{font-size:19px}}
      `}</style>
      <div className="mobile-nav-overlay" onClick={() => setMobileNavOpen(false)} aria-hidden="true" />
      <aside className="sidebar" aria-label="Primary navigation">
        <button className="mobile-nav-close" onClick={() => setMobileNavOpen(false)} aria-label="Close navigation" type="button"><X size={20}/></button>
        <div className="brand"><div className="brand-mark">N</div><span>Nexora</span></div>
        <nav className="sidebar-nav">
          <p className="nav-label">Workspace</p>
          {navigation.map(({ name, path }) => <NavLink key={path} to={path} onClick={() => setMobileNavOpen(false)} className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}><span>{name}</span></NavLink>)}
          <p className="nav-label settings-label">Account</p>
          <NavLink to="/notifications" onClick={() => setMobileNavOpen(false)} className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}><span>Notifications</span></NavLink>
          <NavLink to="/settings" onClick={() => setMobileNavOpen(false)} className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}><span>Settings</span></NavLink>
          <button className="nav-item logout-nav" onClick={logout} type="button"><span>Sign out</span></button>
        </nav>
        <div className="sidebar-user"><div className="avatar">{userInitials}</div><div className="user-copy"><strong>{user.name || "User"}</strong><span>{user.role || "Member"}</span></div></div>
      </aside>
      <main className="main-content">
        <header className="topbar">
          <div className="topbar-spacer"><button className="mobile-menu-button" onClick={() => setMobileNavOpen(true)} aria-label="Open navigation" type="button"><Menu size={19}/></button></div>
          <div className="topbar-actions"><button className="icon-button" aria-label="Notifications" onClick={() => navigate("/notifications")} type="button"><Bell size={17}/></button><button className="top-avatar" onClick={() => navigate("/settings")} aria-label="Account settings" type="button">{userInitials}</button></div>
        </header>
        <section className="page-content"><Outlet /></section>
      </main>
    </div>
  );
}
