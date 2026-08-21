import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Bell, Menu, Repeat2 } from "lucide-react";
import { useEffect, useState } from "react";
import api from "../api";

const navigation=[{name:"Dashboard",path:"/dashboard"},{name:"Projects",path:"/projects"},{name:"Tasks",path:"/tasks"},{name:"Team",path:"/team"},{name:"Analytics",path:"/analytics"},{name:"Activity",path:"/activity"}];
type User={id?:number;name?:string;email?:string;role?:string};
type Workspace={id:number;name:string;role:string;selected?:boolean};
function readUser():User{try{return JSON.parse(localStorage.getItem("nexora_user")||"{}")}catch{return{}}}
function initials(n:string){return(n||"N").trim().split(/\s+/).map(x=>x[0]).join("").slice(0,2).toUpperCase()}
function syncUserRole(role:string){try{const current=readUser();localStorage.setItem("nexora_user",JSON.stringify({...current,role}));}catch{}}

export default function DashboardLayout(){
 const navigate=useNavigate();
 const user=readUser();
 const userInitials=initials(user.name||"Nexora");
 const[mobile,setMobile]=useState(false),[open,setOpen]=useState(false),[workspaces,setWorkspaces]=useState<Workspace[]>([]),[workspace,setWorkspace]=useState<Workspace|null>(null);

 async function load(){
  try{
   const{data}=await api.get("/workspaces");
   const list=data.workspaces||[];
   setWorkspaces(list);
   const stored=localStorage.getItem("nexora_workspace_id");
   const selected=list.find((w:Workspace)=>String(w.id)===stored)||list.find((w:Workspace)=>w.selected)||list[0]||null;
   setWorkspace(selected);
   if(selected){
    localStorage.setItem("nexora_workspace_id",String(selected.id));
    localStorage.setItem("nexora_workspace_role",selected.role);
    syncUserRole(selected.role);
   }
  }catch{}
 }
 useEffect(()=>{void load();const refresh=()=>void load();window.addEventListener("nexora:workspace-changed",refresh);return()=>window.removeEventListener("nexora:workspace-changed",refresh);},[]);

 async function select(w:Workspace){
  try{
   await api.post(`/workspaces/${w.id}/select`);
   localStorage.setItem("nexora_workspace_id",String(w.id));
   localStorage.setItem("nexora_workspace_role",w.role);
   syncUserRole(w.role);
   setWorkspace(w);
   setOpen(false);
   setMobile(false);
   window.dispatchEvent(new CustomEvent("nexora:workspace-changed",{detail:w}));
   navigate("/dashboard",{replace:true});
  }catch{}
 }
 function logout(){["nexora_access_token","nexora_refresh_token","nexora_token","nexora_user","nexora_workspace_id","nexora_workspace_role"].forEach(k=>localStorage.removeItem(k));navigate("/login",{replace:true})}

 return <div className="app-shell">
  <style>{`.workspace-switcher{position:relative;margin:10px 8px 14px}.workspace-trigger{width:100%;display:flex;align-items:center;justify-content:space-between;gap:8px;padding:11px 10px;border:1px solid #e1e4e8;border-radius:9px;background:#f7f8fa;color:#252936;cursor:pointer;text-align:left}.workspace-trigger strong{display:block;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.workspace-menu{position:absolute;z-index:1200;left:0;right:0;top:calc(100% + 6px);padding:5px;background:#fff;border:1px solid #e1e4e8;border-radius:10px;box-shadow:0 12px 30px rgba(23,28,38,.14);max-height:280px;overflow:auto}.workspace-option{width:100%;display:flex;justify-content:space-between;gap:8px;padding:10px;border:0;border-radius:7px;background:transparent;color:#343944;text-align:left;cursor:pointer}.workspace-option:hover,.workspace-option.current{background:#eeecff;color:#4338a8}.workspace-option strong{display:block;font-size:13px}.workspace-option span{font-size:11px;color:#7a818d}.mobile-nav-overlay{display:none}@media(max-width:700px){.mobile-menu-button{display:flex}.mobile-nav-overlay{display:${mobile?"block":"none"};position:fixed;inset:0;background:rgba(17,20,27,.35);z-index:999}.sidebar{width:280px!important;min-width:280px!important;position:fixed!important;left:0;top:0;height:100svh;z-index:1000;overflow:auto;transform:translateX(${mobile?"0":"-105%"});transition:transform .22s ease;background:#fff!important}.sidebar-nav{display:flex!important;flex-direction:column!important;gap:5px!important}.nav-label{display:block!important;color:#7a818d!important;font-size:11px!important;margin:10px 8px 5px!important}.nav-item{display:flex!important;width:100%!important;box-sizing:border-box!important;padding:12px 10px!important}.workspace-menu{position:relative;top:auto;left:auto;right:auto;margin-top:6px;box-shadow:none}.main-content{width:100%;min-width:0}.mobile-menu-button{width:34px;height:34px;align-items:center;justify-content:center;border:1px solid #e1e4e8;border-radius:9px;background:#fff}.page-content{padding:20px 14px 36px}}`}</style>
  <div className="mobile-nav-overlay" onClick={()=>setMobile(false)}/>
  <aside className="sidebar">
   <div className="brand"><div className="brand-mark">N</div><span>Nexora</span></div>
   <div className="workspace-switcher">
    <button className="workspace-trigger" onClick={()=>setOpen(v=>!v)} aria-label="Switch workspace" aria-expanded={open}>
     <strong>{workspace?.name||"Your workspace"}</strong><Repeat2 size={17}/>
    </button>
    {open&&<div className="workspace-menu">{workspaces.map(w=><button key={w.id} className={`workspace-option ${workspace?.id===w.id?"current":""}`} onClick={()=>void select(w)}><div><strong>{w.name}</strong><span>{w.role}</span></div><span>{workspace?.id===w.id?"Current":"Switch"}</span></button>)}</div>}
   </div>
   <nav className="sidebar-nav">{navigation.map(({name,path})=><NavLink key={path} to={path} onClick={()=>setMobile(false)} className={({isActive})=>`nav-item ${isActive?"active":""}`}><span>{name}</span></NavLink>)}<p className="nav-label">Account</p><NavLink to="/notifications" className="nav-item"><span>Notifications</span></NavLink><NavLink to="/settings" className="nav-item"><span>Settings</span></NavLink><button className="nav-item" onClick={logout}><span>Sign out</span></button></nav>
   <div className="sidebar-user"><div className="avatar">{userInitials}</div><div className="user-copy"><strong>{user.name||"User"}</strong><span>{workspace?.role||user.role||"Member"}</span></div></div>
  </aside>
  <main className="main-content"><header className="topbar"><div><button className="mobile-menu-button" onClick={()=>setMobile(true)} aria-label="Open navigation"><Menu size={19}/></button></div><div className="topbar-actions"><button className="icon-button" onClick={()=>navigate("/notifications")} aria-label="Notifications"><Bell size={17}/></button><button className="top-avatar" onClick={()=>navigate("/settings")}>{userInitials}</button></div></header><section className="page-content"><Outlet/></section></main>
 </div>
}
