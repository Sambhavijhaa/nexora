import { useEffect, useState } from "react";
import { BarChart3, CheckCircle2, Circle, Clock3 } from "lucide-react";
import api from "../api";

type Data = { stats: { projects: number; tasks: number; completed: number }; taskBreakdown: { done: number; inProgress: number; todo: number } };
export default function Analytics() {
  const [data, setData] = useState<Data | null>(null);
  useEffect(() => { api.get("/dashboard/summary").then(({ data }) => setData(data)); }, []);
  const total = data ? Math.max(data.stats.tasks, 1) : 1;
  const items = data ? [
    { label: "Completed", value: data.taskBreakdown.done, icon: CheckCircle2 },
    { label: "In Progress", value: data.taskBreakdown.inProgress, icon: Clock3 },
    { label: "Todo", value: data.taskBreakdown.todo, icon: Circle },
  ] : [];
  return <div className="workspace-page"><div className="page-heading"><div><p className="eyebrow">Insights</p><h2>Analytics</h2><p>Understand delivery health from live workspace data.</p></div></div><div className="stats-grid"><div className="stat-card"><div className="stat-icon"><BarChart3 size={19}/></div><p>Total tasks</p><h3>{data?.stats.tasks ?? 0}</h3></div><div className="stat-card"><div className="stat-icon"><CheckCircle2 size={19}/></div><p>Completion rate</p><h3>{data ? Math.round((data.stats.completed / total) * 100) : 0}%</h3></div><div className="stat-card"><div className="stat-icon"><BarChart3 size={19}/></div><p>Projects</p><h3>{data?.stats.projects ?? 0}</h3></div></div><div className="panel analytics-panel"><div className="panel-header"><div><p className="eyebrow">Task health</p><h3>Work distribution</h3></div></div>{items.map(({ label, value, icon: Icon }) => <div className="metric-row" key={label}><div className="metric-label"><Icon size={16}/><strong>{label}</strong><span>{value}</span></div><div className="metric-track"><div style={{ width: `${(value / total) * 100}%` }}/></div></div>)}</div></div>;
}
