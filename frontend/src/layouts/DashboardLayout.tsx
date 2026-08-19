import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Bell, Menu, X } from "lucide-react";
import { useState } from "react";

const navigation = [
  { name: "Dashboard", path: "/dashboard" }, { name: "Projects", path: "/projects" }, { name: "Tasks", path: "/tasks" }, { name: "Team", path: "/team" }, { name: "Analytics", path: "/analytics" }, { name: "Activity", path: "/activity" },
];
type StoredUser = { name?: string; role?: string; email?: string };
function readUser(): StoredUser { try { return JSON.parse(localStorage.getItem("nexora_user") || "{}"); } catch { return {}; } }
function initials(name: string) { return (name || "N").trim().split(/\s+/).map((p) => p[0]).join("").slice(0, 2).toUpperCase(); }

export default function DashboardLayout() {
  const navigate = useNavigate(); const user = readUser(); const userInitials = initials(user.name || "Nexora"); const [mobileNavOpen, setMobileNavOpen] = useState(false);
  function logout() { ["nexora_access_token", "nexora_refresh_token", "nexora_token", "nexora_user"].forEach((key) => localStorage.removeItem(key)); navigate("/login", { replace: true }); }
  return <div className="app-shell">
    <style>{`
      .mobile-menu-button,.mobile-nav-close,.mobile-nav-overlay{display:none}
      @media(max-width:700px){
        .app-shell{min-width:0;overflow-x:hidden;background:#f7f8fa!important}
        .sidebar{width:280px!important;min-width:280px!important;position:fixed!important;left:0;top:0;height:100svh;z-index:1000;overflow-y:auto;transform:translateX(${mobileNavOpen ? "0" : "-105%"});transition:transform .22s ease;background:#fff!important;border-right:1px solid #e1e4e8!important;color:#171a21!important;box-shadow:8px 0 30px rgba(23,28,38,.14)}
        .mobile-nav-overlay{display:${mobileNavOpen ? "block" : "none"};position:fixed;inset:0;background:rgba(17,20,27,.35);z-index:999}
        .mobile-nav-close{display:flex;position:absolute;right:12px;top:12px;width:34px;height:34px;align-items:center;justify-content:center;border:1px solid #e1e4e8;border-radius:8px;background:#fff;color:#171a21;cursor:pointer}
        .brand{color:#171a21!important}.sidebar-nav{display:flex!important;flex-direction:column!important;visibility:visible!important;opacity:1!important;gap:5px!important}
        .nav-label{display:block!important;visibility:visible!important;opacity:1!important;color:#7a818d!important;font-size:11px!important;margin:10px 8px 5px!important}
        .nav-item,.nav-item:visited{display:flex!important;align-items:center!important;width:100%!important;box-sizing:border-box!important;visibility:visible!important;opacity:1!important;color:#343944!important;background:transparent!important;border:0;text-decoration:none;padding:12px 10px!important;font-size:15px!important;line-height:1.3!important;white-space:nowrap!important}
        .nav-item span{display:inline!important;visibility:visible!important;opacity:1!important;color:inherit!important;font-size:inherit!important;line-height:inherit!important;white-space:nowrap!important}
        .nav-item.active{color:#4338a8!important;background:#eeecff!important;box-shadow:inset 3px 0 #5548c9!important}.nav-item:hover{color:#171a21!important;background:#f3f4f7!important}
        .logout-nav{text-align:left!important;font-family:inherit!important;cursor:pointer}.sidebar-user{border-top:1px solid #e1e4e8!important}.user-copy strong{color:#252936!important}.user-copy span{color:#737985!important}
        .main-content{min-width:0;width:100%;background:#f7f8fa!important}.mobile-menu-button{display:flex;width:34px;height:34px;align-items:center;justify-content:center;border:1px solid #e1e4e8;border-radius:9px;background:#fff;color:#252936;cursor:pointer}
        .topbar{padding:0 12px;background:#fff!important;border-bottom:1px solid #e1e4e8}.page-content{padding:20px 14px 36px;max-width:none}.stats-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.dashboard-grid,.analytics-grid,.settings-grid,.card-grid,.member-grid,.task-columns{grid-template-columns:1fr;gap:12px}.form-row{flex-direction:column}.workspace-input{width:100%;min-width:0}.primary-button{width:100%}
      }
      @media(max-width:430px){.sidebar{width:280px!important;min-width:280px!important}.nav-item{font-size:15px!important;padding:12px 9px!important}.page-content{padding-left:11px;padding-right:11px}}
    `}</style>
    <div className="mobile-nav-overlay" onClick={() => setMobileNavOpen(false)} aria-hidden="true" />
    <aside className="sidebar" aria-label="Primary navigation">
      <button className="mobile-nav-close" onClick={() => setMobileNavOpen(false)} aria-label="Close navigation" type="button"><X size={20}/></button>
      <div className="brand"><div className="brand-mark">N</div><span>Nexora</span></div>
      <nav className="sidebar-nav">
        <p className="nav-label">Workspace</p>
        {navigation.map(({name,path}) => <NavLink key={path} to={path} onClick={() => setMobileNavOpen(false)} className={({isActive}) => `nav-item ${isActive ? "active" : ""}`}><span>{name}</span></NavLink>)}
        <p className="nav-label">Account</p>
        <NavLink to="/notifications" onClick={() => setMobileNavOpen(false)} className={({isActive}) => `nav-item ${isActive ? "active" : ""}`}><span>Notifications</span></NavLink>
        <NavLink to="/settings" onClick={() => setMobileNavOpen(false)} className={({isActive}) => `nav-item ${isActive ? "active" : ""}`}><span>Settings</span></NavLink>
        <button className="nav-item logout-nav" onClick={logout} type="button"><span>Sign out</span></button>
      </nav>
      <div className="sidebar-user"><div className="avatar">{userInitials}</div><div className="user-copy"><strong>{user.name || "User"}</strong><span>{user.role || "Member"}</span></div></div>
    </aside>
    <main className="main-content"><header className="topbar"><div className="topbar-spacer"><button className="mobile-menu-button" onClick={() => setMobileNavOpen(true)} aria-label="Open navigation" type="button"><Menu size={19}/></button></div><div className="topbar-actions"><button className="icon-button" aria-label="Notifications" onClick={() => navigate("/notifications")} type="button"><Bell size={17}/></button><button className="top-avatar" onClick={() => navigate("/settings")} aria-label="Account settings" type="button">{userInitials}</button></div></header><section className="page-content"><Outlet /></section></main>
  </div>;
}
