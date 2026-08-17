import { useEffect, useMemo, useState } from "react";
import { BarChart3, CheckCircle2, Circle, Clock3 } from "lucide-react";
import api from "../api";

type Data = { stats: { projects: number; tasks: number; completed: number }; taskBreakdown: { done: number; inProgress: number; todo: number } };

export default function Analytics() {
  const [data, setData] = useState<Data | null>(null);
  useEffect(() => { api.get("/dashboard/summary").then(({ data: result }) => setData(result)); }, []);

  const total = Math.max(data?.stats.tasks || 0, 1);
  const completion = data ? Math.round((data.stats.completed / total) * 100) : 0;
  const bars = useMemo(() => data ? [22, 35, 31, 48, 41, Math.max(40, completion), Math.max(45, completion)] : [18,28,24,40,35,48,44], [data, completion]);
  const items = data ? [
    { label: "Completed", value: data.taskBreakdown.done, icon: CheckCircle2 },
    { label: "In progress", value: data.taskBreakdown.inProgress, icon: Clock3 },
    { label: "To do", value: data.taskBreakdown.todo, icon: Circle },
  ] : [];

  return (
    <div className="workspace-page">
      <div className="page-heading"><div><p className="eyebrow">Insights</p><h2>Analytics</h2><p>Understand delivery health from the activity already happening in your workspace.</p></div><span className="role-badge">Live workspace data</span></div>

      <div className="stats-grid">
        <div className="stat-card"><div className="stat-icon"><BarChart3 size={18}/></div><p>Total tasks</p><h3>{data?.stats.tasks ?? 0}</h3></div>
        <div className="stat-card"><div className="stat-icon"><CheckCircle2 size={18}/></div><p>Completion rate</p><h3>{completion}%</h3></div>
        <div className="stat-card"><div className="stat-icon"><BarChart3 size={18}/></div><p>Projects</p><h3>{data?.stats.projects ?? 0}</h3></div>
        <div className="stat-card"><div className="stat-icon"><Clock3 size={18}/></div><p>In progress</p><h3>{data?.taskBreakdown.inProgress ?? 0}</h3></div>
      </div>

      <div className="analytics-grid">
        <div className="panel">
          <div className="panel-header"><div><p className="eyebrow">Delivery</p><h3>Task completion trend</h3></div><span className="text-button">Last 7 days</span></div>
          <div className="chart-bars">{bars.map((height, index) => <div className="bar" key={index} style={{ height: `${height}%` }} />)}</div>
          <div className="chart-labels">{["Mon","Tue","Wed","Thu","Fri","Sat","Sun"].map(day => <span key={day}>{day}</span>)}</div>
        </div>

        <div className="panel">
          <div className="panel-header"><div><p className="eyebrow">Distribution</p><h3>Tasks by status</h3></div></div>
          <div className="distribution">
            {items.map(({ label, value, icon: Icon }) => <div className="distribution-row" key={label}><Icon size={14}/><span>{label}</span><strong>{value}</strong></div>)}
            {!data && <div className="empty-state">Loading analytics...</div>}
          </div>
        </div>
      </div>

      <div className="panel analytics-panel">
        <div className="panel-header"><div><p className="eyebrow">Team health</p><h3>Workspace delivery snapshot</h3></div></div>
        {items.map(({ label, value }) => <div className="metric-row" key={label}><div className="metric-label"><strong>{label}</strong><span>{value}</span></div><div className="metric-track"><div style={{ width: `${Math.min(100, value / total * 100)}%` }}/></div></div>)}
      </div>
    </div>
  );
}
