import { useEffect, useState } from "react";
import { ArrowUpRight, CheckCircle2, FolderKanban, ListTodo, Users } from "lucide-react";
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

  useEffect(() => {
    api.get("/dashboard/summary").then(({ data }) => setSummary(data)).catch(() => setError("Could not load workspace data."));
  }, []);

  const stats = summary ? [
    { title: "Projects", value: summary.stats.projects, icon: FolderKanban },
    { title: "Total Tasks", value: summary.stats.tasks, icon: ListTodo },
    { title: "Completed", value: summary.stats.completed, icon: CheckCircle2 },
    { title: "Team Members", value: summary.stats.teamMembers, icon: Users },
  ] : [];

  return (
    <div className="dashboard">
      <div className="welcome-section">
        <div>
          <p className="eyebrow">Workspace overview</p>
          <h2>Good morning, {user.name || "there"} <span aria-hidden="true">👋</span></h2>
          <p>Track projects, tasks, people and activity from one production-ready workspace.</p>
        </div>
        <Link className="primary-button" to="/projects">+ New Project</Link>
      </div>

      {error && <div className="form-error page-alert">{error}</div>}
      <div className="stats-grid">
        {stats.map(({ title, value, icon: Icon }) => (
          <div className="stat-card" key={title}>
            <div className="stat-top"><div className="stat-icon"><Icon size={19} /></div><ArrowUpRight size={15} color="#2ca879" /></div>
            <p>{title}</p><h3>{value}</h3>
          </div>
        ))}
      </div>

      <div className="dashboard-grid">
        <div className="panel">
          <div className="panel-header"><div><p className="eyebrow">Projects</p><h3>Project progress</h3></div><Link className="text-button" to="/projects">View all</Link></div>
          {summary?.projects.length ? summary.projects.map((project) => (
            <div className="project-block" key={project.id}>
              <div className="project-row"><div><strong>{project.name}</strong><span>{project.status}</span></div><strong>{project.progress}%</strong></div>
              <div className="progress"><div style={{ width: `${project.progress}%` }} /></div>
            </div>
          )) : <div className="empty-state">Create your first project to start tracking work.</div>}
        </div>

        <div className="panel">
          <div className="panel-header"><div><p className="eyebrow">Activity</p><h3>Recent activity</h3></div><Link className="text-button" to="/analytics">Analytics</Link></div>
          {summary?.activity.length ? summary.activity.map((item) => (
            <div className="activity" key={item.id}><div className="activity-avatar">N</div><div><strong>{item.action}</strong><span>{item.context}</span></div></div>
          )) : <div className="empty-state">Your workspace activity will appear here.</div>}
        </div>
      </div>
    </div>
  );
}
