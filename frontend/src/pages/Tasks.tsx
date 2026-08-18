import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, Circle, Clock3, Plus, Trash2 } from "lucide-react";
import api from "../api";

type Project = { id: number; name: string };
type Task = { id: number; title: string; status: string; priority: string; projectId: number; projectName: string; assignee?: { id: number } | null };
type StoredUser = { id?: number; role?: string };
const columns = ["Todo", "In Progress", "Done"];
function currentUser(): StoredUser { try { return JSON.parse(localStorage.getItem("nexora_user") || "{}") as StoredUser; } catch { return {}; } }

export default function Tasks() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [form, setForm] = useState({ title: "", projectId: "", priority: "Medium" });
  const [error, setError] = useState("");
  const user = currentUser();
  const canCreate = user.role === "Admin" || user.role === "Manager";
  const canManageAll = user.role === "Admin" || user.role === "Manager";

  const load = async () => {
    try {
      const [t, p] = await Promise.all([api.get("/tasks"), api.get("/projects")]);
      setTasks(t.data.tasks || []); setProjects(p.data.projects || []);
      if (!form.projectId && p.data.projects?.[0]) setForm(f => ({ ...f, projectId: String(p.data.projects[0].id) }));
    } catch (err: any) { setError(err.response?.data?.message || "Could not load tasks."); }
  };
  useEffect(() => { load(); }, []);

  async function addTask() {
    if (!canCreate || !form.title.trim() || !form.projectId) return;
    try { await api.post("/tasks", { ...form, projectId: Number(form.projectId) }); setForm(f => ({ ...f, title: "" })); await load(); }
    catch (err: any) { setError(err.response?.data?.message || "Could not create task."); }
  }

  async function changeStatus(task: Task) {
    const canChange = canManageAll || task.assignee?.id === user.id;
    if (!canChange) return;
    const next = task.status === "Todo" ? "In Progress" : task.status === "In Progress" ? "Done" : "Todo";
    try { await api.patch(`/tasks/${task.id}`, { status: next }); await load(); }
    catch (err: any) { setError(err.response?.data?.message || "Could not update task."); }
  }

  async function remove(id: number) {
    if (!canManageAll) return;
    try { await api.delete(`/tasks/${id}`); await load(); }
    catch (err: any) { setError(err.response?.data?.message || "Could not delete task."); }
  }

  const counts = useMemo(() => columns.map(status => ({ status, count: tasks.filter(t => t.status === status).length })), [tasks]);

  return (
    <div className="workspace-page">
      <div className="page-heading">
        <div><p className="eyebrow">Execution</p><h2>Tasks</h2><p>Move work from idea to done and keep every project on track.</p></div>
        <span className="role-badge">{tasks.length} total tasks</span>
      </div>
      {error && <div className="form-error page-alert" role="alert">{error}</div>}

      {canCreate ? (
        <div className="panel create-panel">
          <div><p className="eyebrow">Quick add</p><h3>Create a task</h3><p>Assign it to a project and set the priority before it enters the board.</p></div>
          <div className="form-row">
            <input className="workspace-input" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="e.g. Implement JWT authentication" />
            <select className="workspace-input" value={form.projectId} onChange={e => setForm({ ...form, projectId: e.target.value })}><option value="">Select project</option>{projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select>
            <select className="workspace-input" value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })}><option>Low</option><option>Medium</option><option>High</option></select>
            <button className="primary-button" onClick={addTask}><Plus size={15}/> Add task</button>
          </div>
        </div>
      ) : (
        <div className="panel permission-note"><strong>Member access</strong><span>You can view the board and update tasks assigned to you. Project and task management stays with managers and admins.</span></div>
      )}

      <div className="task-columns">
        {counts.map(({ status, count }) => (
          <div className="task-column" key={status}>
            <div className="column-heading"><span>{status}</span><strong>{count}</strong></div>
            {tasks.filter(t => t.status === status).map(task => {
              const canChange = canManageAll || task.assignee?.id === user.id;
              return <div className="task-card panel" key={task.id}>
                <div className="task-card-top">
                  <button className="task-status" onClick={() => changeStatus(task)} disabled={!canChange} aria-label={canChange ? `Move ${task.title}` : `${task.title} is view only`}>
                    {status === "Done" ? <CheckCircle2 size={15}/> : status === "In Progress" ? <Clock3 size={15}/> : <Circle size={15}/>} 
                  </button>
                  {canManageAll && <button className="danger-button" onClick={() => remove(task.id)} aria-label={`Delete ${task.title}`}><Trash2 size={13}/></button>}
                </div>
                <strong>{task.title}</strong><span>{task.projectName}</span><em className={`priority ${task.priority.toLowerCase()}`}>{task.priority}</em>
              </div>;
            })}
            {!tasks.filter(t => t.status === status).length && <div className="empty-state">No tasks here yet.</div>}
          </div>
        ))}
      </div>
    </div>
  );
}
