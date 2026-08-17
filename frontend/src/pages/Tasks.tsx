import { useEffect, useState } from "react";
import { CheckCircle2, Circle, Clock3, Trash2 } from "lucide-react";
import api from "../api";

type Project = { id: number; name: string };
type Task = { id: number; title: string; status: string; priority: string; projectId: number; projectName: string };

export default function Tasks() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [form, setForm] = useState({ title: "", projectId: "", priority: "Medium" });
  const load = async () => { const [t, p] = await Promise.all([api.get("/tasks"), api.get("/projects")]); setTasks(t.data.tasks); setProjects(p.data.projects); if (!form.projectId && p.data.projects[0]) setForm(f => ({ ...f, projectId: String(p.data.projects[0].id) })); };
  useEffect(() => { load(); }, []);

  async function addTask() { if (!form.title.trim() || !form.projectId) return; await api.post("/tasks", { ...form, projectId: Number(form.projectId) }); setForm(f => ({ ...f, title: "" })); load(); }
  async function changeStatus(task: Task) { const next = task.status === "Todo" ? "In Progress" : task.status === "In Progress" ? "Done" : "Todo"; await api.patch(`/tasks/${task.id}`, { status: next }); load(); }
  async function remove(id: number) { await api.delete(`/tasks/${id}`); load(); }

  return <div className="workspace-page"><div className="page-heading"><div><p className="eyebrow">Execution</p><h2>Tasks</h2><p>Create, prioritize and move work through your delivery pipeline.</p></div></div>
    <div className="panel create-panel"><div><h3>New task</h3><p>Tasks belong to a project and move Todo → In Progress → Done.</p></div><div className="form-row"><input className="workspace-input" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="Task title" /><select className="workspace-input" value={form.projectId} onChange={e => setForm({ ...form, projectId: e.target.value })}><option value="">Select project</option>{projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select><select className="workspace-input" value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })}><option>Low</option><option>Medium</option><option>High</option></select><button className="primary-button" onClick={addTask}>Add task</button></div></div>
    <div className="task-columns">{["Todo", "In Progress", "Done"].map(status => <div className="task-column" key={status}><div className="column-heading"><span>{status}</span><strong>{tasks.filter(t => t.status === status).length}</strong></div>{tasks.filter(t => t.status === status).map(task => <div className="task-card panel" key={task.id}><div className="task-card-top"><button className="task-status" onClick={() => changeStatus(task)}>{status === "Done" ? <CheckCircle2 size={17}/> : status === "In Progress" ? <Clock3 size={17}/> : <Circle size={17}/>}</button><button className="danger-button" onClick={() => remove(task.id)}><Trash2 size={14}/></button></div><strong>{task.title}</strong><span>{task.projectName}</span><em className={`priority ${task.priority.toLowerCase()}`}>{task.priority}</em></div>)}</div>)}</div>
  </div>;
}
