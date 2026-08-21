import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Bell, ChevronDown, Menu, X } from "lucide-react";
import { useEffect, useState } from "react";
import api from "../api";
const navigation=[{name:"Dashboard",path:"/dashboard"},{name:"Projects",path:"/projects"},{name:"Tasks",path:"/tasks"},{name:"Team",path:"/team"},{name:"Analytics",path:"/analytics"},{name:"Activity",path:"/activity"}];
type User={id?:number;name?:string;email?:string;role?:string};type Workspace={id:number;name:string;role:string;selected?:boolean};
function readUser():User{try{return JSON.parse(localStorage.getItem("nexora_user")||"{}")}catch{return{}}}function initials(n:string){return(n||"N").trim().split(/\s+/).map(x=>x[0]).join("").slice(0,2).toUpperCase()}function syncUserRole(role:string){try{const u=readUser();localStorage.setItem("nexora_user",JSON.stringify({...u,role}))}catch{}}
export default function DashboardLayout(){const navigate=useNavigate();const user=readUser();const userInitials=initials(user.name||"Nexora");const[open,setOpen]=useState(false),[drawer,setDrawer]=useState(false),[workspaces,setWorkspaces]=useState<Workspace[]>([]),[workspace,setWorkspace]=useState<Workspace|null>(null);
async function load(){try{const{data}=await api.get("/workspaces");const list=data.workspaces||[];setWorkspaces(list);const stored=localStorage.getItem("nexora_workspace_id");const selected=list.find((w:Workspace)=>String(w.id)===stored)||list.find((w:Workspace)=>w.selected)||list[0]||null;setWorkspace(selected);if(selected){localStorage.setItem("nexora_workspace_id",String(selected.id));localStorage.setItem("nexora_workspace_role",selected.role);syncUserRole(selected.role)}}catch{}}
useEffect(()=>{void load();const refresh=()=>void load();window.addEventListener("nexora:workspace-changed",refresh);return()=>window.removeEventListener("nexora:workspace-changed",refresh)},[]);
function select(w:Workspace){localStorage.setItem("nexora_workspace_id",String(w.id));localStorage.setItem("nexora_workspace_role",w.role);syncUserRole(w.role);setWorkspace(w);setOpen(false);setDrawer(false);window.dispatchEvent(new CustomEvent("nexora:workspace-changed",{detail:w}));navigate("/dashboard",{replace:true})}function logout(){["nexora_access_token","nexora_refresh_token","nexora_token","nexora_user","nexora_workspace_id","nexora_workspace_role"].forEach(k=>localStorage.removeItem(k));navigate("/login",{replace:true})}
return <div className="app-shell"><style>{`
.workspace-switcher{position:relative}.workspace-trigger{display:flex;align-items:center;gap:10px;width:100%;border:1px solid transparent!important;border-radius:12px!important;background:transparent!important;box-shadow:none!important;padding:8px 10px!important;color:inherit!important;cursor:pointer}.workspace-trigger::before{content:"";width:32px;height:32px;flex:0 0 32px;border-radius:10px;background:linear-gradient(135deg,#8b72ff,#5b4acb);display:block}.workspace-trigger strong{font-size:13px;flex:1;text-align:left;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.workspace-menu{position:absolute;left:0;top:calc(100% + 8px);min-width:290px;padding:8px;border:1px solid rgba(255,255,255,.1);border-radius:16px;background:#151922;box-shadow:0 18px 50px rgba(0,0,0,.38);z-index:6000}.workspace-menu::before{content:"WORKSPACES";display:block;padding:4px 10px 8px;color:#8992a3;font-size:10px;font-weight:700;letter-spacing:.08em}.workspace-option{display:flex;align-items:center;gap:10px;width:100%;min-height:58px;padding:9px 10px;border:0;border-radius:11px;background:transparent;color:#e8ebf2;cursor:pointer;text-align:left}.workspace-option::before{content:"";width:34px;height:34px;flex:0 0 34px;border-radius:10px;background:linear-gradient(135deg,#8b72ff,#5b4acb)}.workspace-option:hover{background:#222735}.workspace-option.current{background:rgba(137,112,255,.13)}.workspace-option>div{min-width:0;flex:1;display:flex;flex-direction:column;gap:3px}.workspace-option strong{font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.workspace-option div span{font-size:11px;color:#8992a3}.workspace-option>span:last-child{font-size:11px;font-weight:700;color:#9c8cff}
.mobile-menu-button,.mobile-overlay,.mobile-close{display:none}
@media (max-width: 700px) {
  body:has(.sidebar.mobile-open) {
    overflow: hidden !important;
  }

  /* Hamburger */
  .mobile-menu-button {
    display: flex !important;
    position: fixed !important;
    top: 10px !important;
    left: 10px !important;
    z-index: 10001 !important;
    width: 44px !important;
    height: 44px !important;
    align-items: center !important;
    justify-content: center !important;
    border: 1px solid #303746 !important;
    border-radius: 10px !important;
    background: #171c25 !important;
    color: #fff !important;
  }

  /* Dark background */
  .mobile-overlay {
    display: block !important;
    position: fixed !important;
    inset: 0 !important;
    width: 100vw !important;
    height: 100dvh !important;
    background: rgba(0, 0, 0, 0.6) !important;
    border: 0 !important;
    z-index: 9998 !important;
  }

  /* Mobile drawer */
  .sidebar {
    position: fixed !important;
    inset: 0 auto 0 0 !important;
    width: min(310px, 86vw) !important;
    height: 100dvh !important;
    min-height: 100dvh !important;

    transform: translate3d(-105%, 0, 0) !important;
    transition: transform 0.25s ease !important;

    z-index: 10000 !important;

    display: flex !important;
    flex-direction: column !important;
    align-items: stretch !important;

    overflow: hidden !important;

    padding: 16px !important;
    margin: 0 !important;
    box-sizing: border-box !important;

    background: #11151d !important;
    color: #e8ebf2 !important;
    visibility: visible !important;
    opacity: 1 !important;
  }

  .sidebar.mobile-open {
    transform: translate3d(0, 0, 0) !important;
  }

  /* Header */
  .sidebar .brand {
    display: flex !important;
    align-items: center !important;
    flex: 0 0 auto !important;
    width: 100% !important;
    min-height: 48px !important;
    padding: 4px 48px 12px 8px !important;
    box-sizing: border-box !important;
  }

  /* Close button */
  .mobile-close {
    display: flex !important;
    position: absolute !important;
    top: 12px !important;
    right: 10px !important;
    z-index: 10002 !important;

    width: 38px !important;
    height: 38px !important;

    align-items: center !important;
    justify-content: center !important;

    border: 0 !important;
    border-radius: 9px !important;
    background: rgba(255,255,255,.06) !important;
    color: #fff !important;
  }

  /* Workspace */
  .workspace-switcher {
    position: relative !important;
    flex: 0 0 auto !important;
    width: 100% !important;
    margin: 0 0 14px !important;
  }

  .workspace-trigger {
    width: 100% !important;
    min-height: 48px !important;
  }

  /*
    IMPORTANT:
    Keep workspace menu inside the drawer.
    Don't use position:fixed here.
  */
  .workspace-menu {
    position: absolute !important;
    left: 0 !important;
    right: 0 !important;
    top: calc(100% + 8px) !important;

    width: 100% !important;
    min-width: 0 !important;

    max-height: 50dvh !important;
    overflow-y: auto !important;

    z-index: 10003 !important;
  }

  /* Navigation container */
  .sidebar-nav {
    display: flex !important;
    flex-direction: column !important;
    align-items: stretch !important;

    flex: 1 1 auto !important;
    width: 100% !important;
    min-height: 0 !important;

    overflow-y: auto !important;
    overflow-x: hidden !important;

    padding: 4px 2px 16px !important;
    margin: 0 !important;

    box-sizing: border-box !important;
  }

  /* Every navigation item */
  .sidebar-nav .nav-item,
  .sidebar-nav a.nav-item,
  .sidebar-nav button.nav-item {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;

    position: relative !important;

    flex: 0 0 auto !important;
    width: 100% !important;
    min-width: 0 !important;
    height: 48px !important;
    min-height: 48px !important;

    align-items: center !important;
    justify-content: flex-start !important;

    padding: 0 14px !important;
    margin: 0 0 4px !important;

    box-sizing: border-box !important;

    color: #e8ebf2 !important;
    background: transparent !important;

    border: 0 !important;
    border-radius: 10px !important;

    text-align: left !important;
    white-space: nowrap !important;
    overflow: visible !important;
  }

  .sidebar-nav .nav-item span {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;

    color: inherit !important;
    font-size: 14px !important;
    line-height: 1 !important;
  }

  .sidebar-nav .nav-item:hover {
    background: rgba(255,255,255,.06) !important;
  }

  .sidebar-nav .nav-item.active {
    background: rgba(137,112,255,.16) !important;
    color: #fff !important;
  }

  /* Account heading */
  .nav-label {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;

    flex: 0 0 auto !important;

    margin: 18px 10px 7px !important;
    padding: 0 !important;

    color: #8992a3 !important;
    font-size: 10px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: .08em !important;
  }

  /* User at bottom */
  .sidebar-user {
    display: flex !important;
    flex: 0 0 auto !important;

    width: 100% !important;
    min-height: 58px !important;

    align-items: center !important;

    margin: 0 !important;
    padding: 10px 8px !important;

    box-sizing: border-box !important;

    border-top: 1px solid rgba(255,255,255,.08) !important;
  }

  /* Main page stays underneath drawer */
  .main-content {
    width: 100% !important;
    min-width: 0 !important;
    margin: 0 !important;
  }

  .page-content {
    width: 100% !important;
    padding: 68px 12px 30px !important;
    box-sizing: border-box !important;
  }

  .topbar {
    height: 56px !important;
    padding: 0 12px 0 64px !important;
  }

  /* Task board */
  .task-board-scroll {
    width: 100% !important;
    max-width: 100% !important;
    overflow-x: auto !important;
    overflow-y: visible !important;
    -webkit-overflow-scrolling: touch !important;
  }

  .task-columns {
    min-width: 1280px !important;
  }

  .task-column {
    min-width: 245px !important;
  }
}
}
`}</style><button className="mobile-menu-button" onClick={()=>setDrawer(true)} aria-label="Open navigation"><Menu size={21}/></button>{drawer&&<button className="mobile-overlay" onClick={()=>setDrawer(false)} aria-label="Close navigation"/>}<aside className={`sidebar ${drawer?"mobile-open":""}`}><button className="mobile-close" onClick={()=>setDrawer(false)} aria-label="Close navigation"><X size={20}/></button><div className="brand"><div className="brand-mark">N</div><span>Nexora</span></div><div className="workspace-switcher"><button className="workspace-trigger" onClick={()=>setOpen(v=>!v)} aria-label="Switch workspace"><strong>{workspace?.name||"Your workspace"}</strong><ChevronDown size={16}/></button>{open&&<div className="workspace-menu">{workspaces.map(w=><button key={w.id} className={`workspace-option ${workspace?.id===w.id?"current":""}`} onClick={()=>select(w)}><div><strong>{w.name}</strong><span>{w.role}</span></div><span>{workspace?.id===w.id?"✓":""}</span></button>)}</div>}</div><nav className="sidebar-nav">{navigation.map(({name,path})=><NavLink key={path} to={path} onClick={()=>setDrawer(false)} className={({isActive})=>`nav-item ${isActive?"active":""}`}><span>{name}</span></NavLink>)}<p className="nav-label">Account</p><NavLink to="/notifications" onClick={()=>setDrawer(false)} className="nav-item"><span>Notifications</span></NavLink><NavLink to="/settings" onClick={()=>setDrawer(false)} className="nav-item"><span>Settings</span></NavLink><button className="nav-item" onClick={logout}><span>Sign out</span></button></nav><div className="sidebar-user"><div className="avatar">{userInitials}</div><div className="user-copy"><strong>{user.name||"User"}</strong><span>{workspace?.role||user.role||"Member"}</span></div></div></aside><main className="main-content"><header className="topbar"><div></div><div className="topbar-actions"><button className="icon-button" onClick={()=>navigate("/notifications")} aria-label="Notifications"><Bell size={17}/></button><button className="top-avatar" onClick={()=>navigate("/settings")}>{userInitials}</button></div></header><section className="page-content"><Outlet/></section></main></div>
