import { useEffect, useState } from "react";
import { CheckCircle2, FolderKanban, ListTodo, Users } from "lucide-react";
import { Link } from "react-router-dom";
import api from "../api";

type Summary = {
  stats: { projects: number; tasks: number; completed: number; teamMembers: number };
  taskBreakdown: { done: number; inProgress: number; todo: number };
  projects: Array<{ id: number; name: string; progress: number; status: string }>;
  activity: Array<{ id: number; action: string; context: string }>;
};

export default function Dashboard() {
  const user = JSON.parse(localStorage.getItem("nexora_user") || "{}") as { name?: string };
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { api.get("/dashboard/summary").then(({ data }) => setSummary(data)).catch((err) => setError(err.response?.data?.message || "Could not load workspace data.")); }, []);
  const stats = summary ? [
    { title: "Projects", value: summary.stats.projects, icon: FolderKanban },
    { title: "Open tasks", value: summary.stats.tasks - summary.stats.completed, icon: ListTodo },
    { title: "Completed", value: summary.stats.completed, icon: CheckCircle2 },
    { title: "Team", value: summary.stats.teamMembers, icon: Users },
  ] : [];
  const totalTasks = summary?.stats.tasks || 0;
  const completedTasks = summary?.taskBreakdown.done || 0;
  const completion = totalTasks ? Math.round(completedTasks / totalTasks * 100) : 0;

  return <div className="dashboard">
    <div className="welcome-section"><div><p className="eyebrow">Workspace overview</p><h2>Good morning, {user.name || "there"}</h2><p>Projects, people, tasks, and progress connected in one place.</p></div><Link className="primary-button" to="/projects">+ New Project</Link></div>
    {error && <div className="form-error page-alert">{error}</div>}
    <div className="stats-grid">{stats.map(({ title, value, icon: Icon }) => <div className="stat-card" key={title}><div className="stat-icon"><Icon size={17} /></div><p>{title}</p><h3>{value}</h3></div>)}</div>

    <div className="analytics-grid">
      <div className="panel"><div className="panel-header"><div><p className="eyebrow">Tasks</p><h3>Completion</h3></div><Link className="text-button" to="/tasks">View tasks</Link></div><div style={{display:"flex",alignItems:"baseline",gap:10}}><strong style={{fontSize:32,color:"#252936"}}>{completion}%</strong><span style={{fontSize:13,color:"#737985"}}>{completedTasks} of {totalTasks} tasks completed</span></div><div className="progress" style={{marginTop:16}}><div style={{width:`${completion}%`}} /></div><div className="distribution" style={{marginTop:18}}><div className="distribution-row"><span className="distribution-dot" />To do <strong>{summary?.taskBreakdown.todo || 0}</strong></div><div className="distribution-row"><span className="distribution-dot" />In progress <strong>{summary?.taskBreakdown.inProgress || 0}</strong></div><div className="distribution-row"><span className="distribution-dot" />Completed <strong>{completedTasks}</strong></div></div></div>
      <div className="panel"><div className="panel-header"><div><p className="eyebrow">People</p><h3>Workspace team</h3></div><Link className="text-button" to="/team">View team</Link></div><div style={{display:"flex",alignItems:"baseline",gap:10}}><strong style={{fontSize:32,color:"#252936"}}>{summary?.stats.teamMembers || 0}</strong><span style={{fontSize:13,color:"#737985"}}>workspace members</span></div><p style={{marginTop:12,color:"#737985",fontSize:13}}>Invite members from Team and assign them to projects and tasks.</p></div>
    </div>

    <div className="dashboard-grid" style={{ marginTop: 16 }}>
      <div className="panel"><div className="panel-header"><div><p className="eyebrow">Projects</p><h3>Project performance</h3></div><Link className="text-button" to="/projects">View all</Link></div>{summary?.projects.length ? summary.projects.map((project) => <Link className="project-block dashboard-project-link" to={`/projects/${project.id}`} key={project.id}><div className="project-row"><div><strong>{project.name}</strong><span>{project.status}</span></div><strong>{project.progress}%</strong></div><div className="progress"><div style={{ width: `${project.progress}%` }} /></div><small style={{display:"block",marginTop:7,color:"#5548c9",fontWeight:700}}>Open project →</small></Link>) : <div className="empty-state">Create your first project to start tracking delivery.</div>}</div>
      <div className="panel"><div className="panel-header"><div><p className="eyebrow">Activity</p><h3>Recent activity</h3></div><Link className="text-button" to="/activity">View all</Link></div>{summary?.activity.length ? summary.activity.map((item) => <div className="activity" key={item.id}><div className="activity-avatar">N</div><div><strong>{item.action}</strong><span>{item.context}</span></div></div>) : <div className="empty-state">Workspace activity will appear here.</div>}</div>
    </div>
    <style>{`.dashboard-project-link{display:block;color:inherit;text-decoration:none;cursor:pointer;border-radius:9px;padding:9px;transition:background .15s ease}.dashboard-project-link:hover{background:#f7f8fa}.dashboard-project-link:focus-visible{outline:2px solid #5548c9;outline-offset:2px}`}</style>
  </div>;
}
