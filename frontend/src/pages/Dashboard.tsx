import { useEffect, useMemo, useState } from "react";
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
    api.get("/dashboard/summary")
      .then(({ data }) => setSummary(data))
      .catch((err) => setError(err.response?.data?.message || "Could not load workspace data."));
  }, []);

  const stats = summary ? [
    { title: "Active projects", value: summary.stats.projects, change: "Live", icon: FolderKanban },
    { title: "Active tasks", value: summary.stats.tasks - summary.stats.completed, change: "Across workspace", icon: ListTodo },
    { title: "Completed", value: summary.stats.completed, change: "Delivery", icon: CheckCircle2 },
    { title: "Team members", value: summary.stats.teamMembers, change: "Workspace", icon: Users },
  ] : [];

  const bars = useMemo(() => {
    if (!summary) return [20, 35, 28, 55, 44, 68, 58];
    const total = Math.max(summary.stats.tasks, 1);
    const done = summary.taskBreakdown.done;
    return [25, 34, 29, Math.max(30, done / total * 100), 52, Math.max(38, done / total * 100), Math.max(42, done / total * 100)];
  }, [summary]);

  return (
    <div className="dashboard">
      <div className="welcome-section">
        <div>
          <p className="eyebrow">Workspace overview</p>
          <h2>Good morning, {user.name || "there"} <span aria-hidden="true">👋</span></h2>
          <p>Plan projects, coordinate your team and keep delivery moving from one workspace.</p>
        </div>
        <Link className="primary-button" to="/projects">+ New Project</Link>
      </div>

      {error && <div className="form-error page-alert">{error}</div>}

      <div className="stats-grid">
        {stats.map(({ title, value, change, icon: Icon }) => (
          <div className="stat-card" key={title}>
            <div className="stat-top"><div className="stat-icon"><Icon size={18} /></div><span className="stat-change"><ArrowUpRight size={13} /> {change}</span></div>
            <p>{title}</p><h3>{value}</h3>
          </div>
        ))}
      </div>

      <div className="analytics-grid">
        <div className="panel">
          <div className="panel-header">
            <div><p className="eyebrow">Performance</p><h3>Task completion</h3></div>
            <span className="text-button">Last 7 days</span>
          </div>
          <div className="chart-bars">
            {bars.map((height, index) => <div className="bar" key={index} style={{ height: `${height}%` }} />)}
          </div>
          <div className="chart-labels">{["Mon","Tue","Wed","Thu","Fri","Sat","Sun"].map(day => <span key={day}>{day}</span>)}</div>
        </div>

        <div className="panel">
          <div className="panel-header"><div><p className="eyebrow">Task health</p><h3>Work distribution</h3></div></div>
          {summary ? (
            <div className="distribution">
              <div className="distribution-row"><span className="distribution-dot" />To do <strong>{summary.taskBreakdown.todo}</strong></div>
              <div className="distribution-row"><span className="distribution-dot" />In progress <strong>{summary.taskBreakdown.inProgress}</strong></div>
              <div className="distribution-row"><span className="distribution-dot" />Completed <strong>{summary.taskBreakdown.done}</strong></div>
            </div>
          ) : <div className="empty-state">Loading workspace metrics...</div>}
        </div>
      </div>

      <div className="dashboard-grid" style={{ marginTop: 16 }}>
        <div className="panel">
          <div className="panel-header"><div><p className="eyebrow">Projects</p><h3>Project performance</h3></div><Link className="text-button" to="/projects">View all</Link></div>
          {summary?.projects.length ? summary.projects.map((project) => (
            <div className="project-block" key={project.id}>
              <div className="project-row"><div><strong>{project.name}</strong><span>{project.status}</span></div><strong>{project.progress}%</strong></div>
              <div className="progress"><div style={{ width: `${project.progress}%` }} /></div>
            </div>
          )) : <div className="empty-state">Create your first project to start tracking delivery.</div>}
        </div>

        <div className="panel">
          <div className="panel-header"><div><p className="eyebrow">Timeline</p><h3>Recent activity</h3></div><Link className="text-button" to="/activity">View all</Link></div>
          {summary?.activity.length ? summary.activity.map((item) => (
            <div className="activity" key={item.id}><div className="activity-avatar">N</div><div><strong>{item.action}</strong><span>{item.context}</span></div></div>
          )) : <div className="empty-state">Your workspace activity will appear here.</div>}
        </div>
      </div>
    </div>
  );
}
