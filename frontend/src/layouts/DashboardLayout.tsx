import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Bell, Repeat2 } from "lucide-react";
import { useEffect, useState } from "react";
import api from "../api";

const navigation=[{name:"Dashboard",path:"/dashboard"},{name:"Projects",path:"/projects"},{name:"Tasks",path:"/tasks"},{name:"Team",path:"/team"},{name:"Analytics",path:"/analytics"},{name:"Activity",path:"/activity"}];
type User={id?:number;name?:string;email?:string;role?:string};
type Workspace={id:number;name:string;role:string;selected?:boolean};
function readUser():User{try{return JSON.parse(localStorage.getItem("nexora_user")||"{}")}catch{return{}}}
function initials(n:string){return(n||"N").trim().split(/\s+/).map(x=>x[0]).join("").slice(0,2).toUpperCase()}
function syncUserRole(role:string){try{const current=readUser();localStorage.setItem("nexora_user",JSON.stringify({...current,role}));}catch{}}

export default function DashboardLayout(){
 const navigate=useNavigate(); const user=readUser(); const userInitials=initials(user.name||"Nexora");
 const[open,setOpen]=useState(false),[workspaces,setWorkspaces]=useState<Workspace[]>([]),[workspace,setWorkspace]=useState<Workspace|null>(null);
 async function load(){try{const{data}=await api.get("/workspaces");const list=data.workspaces||[];setWorkspaces(list);const stored=localStorage.getItem("nexora_workspace_id");const selected=list.find((w:Workspace)=>String(w.id)===stored)||list.find((w:Workspace)=>w.selected)||list[0]||null;setWorkspace(selected);if(selected){localStorage.setItem("nexora_workspace_id",String(selected.id));localStorage.setItem("nexora_workspace_role",selected.role);syncUserRole(selected.role);}}catch{}}
 useEffect(()=>{void load();const refresh=()=>void load();window.addEventListener("nexora:workspace-changed",refresh);return()=>window.removeEventListener("nexora:workspace-changed",refresh)},[]);
 function select(w:Workspace){localStorage.setItem("nexora_workspace_id",String(w.id));localStorage.setItem("nexora_workspace_role",w.role);syncUserRole(w.role);setWorkspace(w);setOpen(false);window.dispatchEvent(new CustomEvent("nexora:workspace-changed",{detail:w}));navigate("/dashboard",{replace:true})}
 function logout(){["nexora_access_token","nexora_refresh_token","nexora_token","nexora_user","nexora_workspace_id","nexora_workspace_role"].forEach(k=>localStorage.removeItem(k));navigate("/login",{replace:true})}
 return <div className="app-shell">
  <style>{`@media(max-width:700px){
   .app-shell{display:block!important;min-height:100svh!important}.main-content{width:100%!important;min-width:0!important;padding-bottom:88px!important}.page-content{width:100%!important;box-sizing:border-box!important;padding:16px 12px 30px!important}
   .sidebar{position:fixed!important;left:0!important;right:0!important;bottom:0!important;top:auto!important;width:100%!important;min-width:0!important;height:76px!important;min-height:76px!important;max-height:none!important;padding:0!important;z-index:2000!important;display:block!important;overflow:visible!important;background:#11151d!important;border-top:1px solid #2b313c!important}
   .sidebar .brand,.sidebar-user,.nav-label{display:none!important}.workspace-switcher{position:absolute!important;left:12px!important;right:12px!important;bottom:calc(100% + 10px)!important;margin:0!important}.workspace-trigger{height:42px!important;box-sizing:border-box!important;background:#171c25!important;border-color:#303746!important;color:#fff!important}.workspace-menu{bottom:calc(100% + 6px)!important;top:auto!important;max-height:45vh!important;background:#171c25!important;border-color:#303746!important}.workspace-option{color:#fff!important}
   .sidebar-nav{height:76px!important;width:100%!important;display:grid!important;grid-template-columns:repeat(6,minmax(0,1fr))!important;align-items:stretch!important;gap:0!important;padding:5px 3px calc(5px + env(safe-area-inset-bottom))!important;box-sizing:border-box!important;overflow:hidden!important}
   .sidebar-nav .nav-item{display:flex!important;flex-direction:column!important;align-items:center!important;justify-content:center!important;width:100%!important;height:64px!important;min-width:0!important;padding:5px 1px!important;margin:0!important;box-sizing:border-box!important;border:0!important;background:transparent!important;color:#8b94a5!important;font-size:10px!important;font-weight:600!important;line-height:1.15!important;text-align:center!important;white-space:normal!important;overflow:visible!important}
   .sidebar-nav .nav-item span{display:block!important;width:100%!important;overflow:hidden!important;text-overflow:ellipsis!important}.sidebar-nav .nav-item.active{color:#fff!important;background:#252033!important;border-radius:10px!important;box-shadow:none!important}.sidebar-nav .nav-item:nth-last-child(-n+3){display:none!important}
   .topbar{height:56px!important;padding:0 12px!important}.topbar-search{display:none!important}.topbar-actions{margin-left:auto!important}.welcome-section,.page-heading{width:100%!important;box-sizing:border-box!important}.stats-grid,.dashboard-grid,.card-grid,.member-grid,.analytics-grid{width:100%!important;box-sizing:border-box!important}
  }
  @media(max-width:380px){.sidebar-nav .nav-item{font-size:9px!important}.sidebar-nav{padding-left:1px!important;padding-right:1px!important}.sidebar-nav .nav-item{padding-left:0!important;padding-right:0!important}.workspace-trigger strong{font-size:11px!important}}
  `}</style>
  <aside className="sidebar">
   <div className="brand"><div className="brand-mark">N</div><span>Nexora</span></div>
   <div className="workspace-switcher"><button className="workspace-trigger" onClick={()=>setOpen(v=>!v)} aria-label="Switch workspace" aria-expanded={open}><strong>{workspace?.name||"Your workspace"}</strong><Repeat2 size={17}/></button>{open&&<div className="workspace-menu">{workspaces.map(w=><button key={w.id} className={`workspace-option ${workspace?.id===w.id?"current":""}`} onClick={()=>select(w)}><div><strong>{w.name}</strong><span>{w.role}</span></div><span>{workspace?.id===w.id?"Current":"Switch"}</span></button>)}</div>}</div>
   <nav className="sidebar-nav">{navigation.map(({name,path})=><NavLink key={path} to={path} className={({isActive})=>`nav-item ${isActive?"active":""}`}><span>{name}</span></NavLink>)}<p className="nav-label">Account</p><NavLink to="/notifications" className="nav-item"><span>Notifications</span></NavLink><NavLink to="/settings" className="nav-item"><span>Settings</span></NavLink><button className="nav-item" onClick={logout}><span>Sign out</span></button></nav>
   <div className="sidebar-user"><div className="avatar">{userInitials}</div><div className="user-copy"><strong>{user.name||"User"}</strong><span>{workspace?.role||user.role||"Member"}</span></div></div>
  </aside>
  <main className="main-content"><header className="topbar"><div></div><div className="topbar-actions"><button className="icon-button" onClick={()=>navigate("/notifications")} aria-label="Notifications"><Bell size={17}/></button><button className="top-avatar" onClick={()=>navigate("/settings")}>{userInitials}</button></div></header><section className="page-content"><Outlet/></section></main>
 </div>
}