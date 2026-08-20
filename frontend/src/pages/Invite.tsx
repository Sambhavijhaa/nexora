import { useEffect, useState } from "react";
import { ArrowRight, CheckCircle2, ShieldCheck } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import api from "../api";

export default function Invite(){
  const { token="" }=useParams(); const navigate=useNavigate(); const [status,setStatus]=useState<"ready"|"accepted"|"error">("ready"); const [message,setMessage]=useState("Checking invitation…");
  useEffect(()=>{ if(!token){setStatus("error");setMessage("This invitation link is invalid.");return;} localStorage.setItem("nexora_invitation_token",token); },[token]);
  async function accept(){
    const access=localStorage.getItem("nexora_access_token")||localStorage.getItem("nexora_token");
    if(!access){navigate("/login",{replace:true});return;}
    try{await api.post("/team/accept",{token});localStorage.removeItem("nexora_invitation_token");setStatus("accepted");setMessage("You have joined the workspace successfully.");setTimeout(()=>navigate("/dashboard",{replace:true}),900);}catch(err:any){setStatus("error");setMessage(err.response?.data?.message||"This invitation could not be accepted.");}
  }
  const loggedIn=!!(localStorage.getItem("nexora_access_token")||localStorage.getItem("nexora_token"));
  return <main className="auth-page"><section className="auth-card invite-page-card"><div className="auth-brand"><span className="brand-mark">N</span><strong>Nexora</strong></div>{status==="accepted"?<><div className="invite-big-icon"><CheckCircle2 size={28}/></div><p className="eyebrow">Invitation accepted</p><h1>Welcome to the workspace</h1><p className="auth-subtitle">{message}</p></>:<><div className="invite-big-icon"><ShieldCheck size={28}/></div><p className="eyebrow">Workspace invitation</p><h1>You're invited to Nexora</h1><p className="auth-subtitle">Join your team workspace and start working on projects and tasks together.</p>{status==="error"&&<div className="form-error" role="alert">{message}</div>}{status!=="error"&&(loggedIn?<button className="primary-button auth-submit" onClick={accept}>Accept invitation <ArrowRight size={16}/></button>:<><button className="primary-button auth-submit" onClick={()=>navigate("/login")}>Sign in to accept <ArrowRight size={16}/></button><p className="auth-footer">New to Nexora? <Link to="/register">Create your account</Link></p></>)}</>}</section><style>{`.invite-page-card{text-align:center}.invite-page-card .auth-brand{justify-content:center}.invite-big-icon{width:58px;height:58px;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:24px auto 18px;background:#eeecff;color:#5548c9}.invite-page-card .form-error{margin:18px 0}.invite-page-card .auth-submit{margin-top:22px}`}</style></main>
}
