import { useEffect, useMemo, useState } from "react";
import { CalendarDays, CheckCircle2, Circle, Clock3, Plus, Search, Trash2 } from "lucide-react";
import api from "../api";

type Project = { id: number; name: string };
type Member = { id: number; name: string; email: string; role: string };
type Task = {
  id: number; title: string; description: string; status: string; priority: string;
  projectId: number; projectName: string; dueDate?: string | null; createdAt?: string | null;
  assignee?: { id: number; name: string; email: string; role: string } | null;
};
type StoredUser = { id?: number; role?: string };

const columns = ["Todo", "In Progress", "Review", "Blocked", "Done"];
const statuses = ["Todo", "In Progress", "Review", "Blocked", "Done"];

function currentUser(): StoredUser { try { return JSON.parse(localStorage.getItem("nexora_user") || "{}") as StoredUser; } catch { return {}; } }
function formatDate(value?: string | null) { if (!value) return "No due date"; const d = new Date(value); return Number.isNaN(d.getTime()) ? value : d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }); }

export default function Tasks() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [form, setForm] = useState({ title: "", description: "", projectId: "", assigneeId: "", priority: "Medium", dueDate: "" });
  const [filters, setFilters] = useState({ search: "", projectId: "", assigneeId: "", status: "", priority: "" });
  const [error, setError] = useState("");
  const user = currentUser();
  const canCreate = user.role === "Admin" || user.role === "Manager";
  const canManageAll = user.role === "Admin" || user.role === "Manager";

  const load = async () => {
    try {
      const [t, p, team] = await Promise.all([api.get("/tasks"), api.get("/projects"), api.get("/team")]);
      setTasks(t.data.tasks || []); setProjects(p.data.projects || []); setMembers(team.data.members || []);
      if (!form.projectId && p.data.projects?.[0]) setForm(f => ({ ...f, projectId: String(p.data.projects[0].id) }));
    } catch (err: any) { setError(err.response?.data?.message || "Could not load tasks."); }
  };
  useEffect(() => { load(); }, []);

  async function addTask() {
    if (!canCreate || !form.title.trim() || !form.projectId) return;
    setError("");
    try {
      await api.post("/tasks", { title: form.title.trim(), description: form.description.trim(), projectId: Number(form.projectId), priority: form.priority, assigneeId: form.assigneeId ? Number(form.assigneeId) : null, dueDate: form.dueDate || null, status: "Todo" });
      setForm(f => ({ ...f, title: "", description: "", assigneeId: "", dueDate: "" })); await load();
    } catch (err: any) { setError(err.response?.data?.message || "Could not create task."); }
  }

  async function changeStatus(task: Task, status: string) {
    const isAssignee = task.assignee?.id === user.id;
    if (!canManageAll && !isAssignee) return;
    if (status === task.status) return;
    try { await api.patch(`/tasks/${task.id}`, { status }); await load(); }
    catch (err: any) { setError(err.response?.data?.message || "Could not update task."); }
  }

  async function remove(id: number) {
    if (!canManageAll) return;
    try { await api.delete(`/tasks/${id}`); await load(); }
    catch (err: any) { setError(err.response?.data?.message || "Could not delete task."); }
  }

  const filteredTasks = useMemo(() => tasks.filter(task => {
    const q = filters.search.trim().toLowerCase();
    return (!q || task.title.toLowerCase().includes(q) || task.projectName.toLowerCase().includes(q) || task.assignee?.name.toLowerCase().includes(q))
      && (!filters.projectId || String(task.projectId) === filters.projectId)
      && (!filters.assigneeId || String(task.assignee?.id || "") === filters.assigneeId)
      && (!filters.status || task.status === filters.status)
      && (!filters.priority || task.priority === filters.priority);
  }), [tasks, filters]);

  return <div className="workspace-page">
    <div className="page-heading"><div><p className="eyebrow">Execution</p><h2>Tasks</h2><p>Every task belongs to a project, has an owner, a status, a priority and an optional deadline.</p></div><span className="role-badge">{filteredTasks.length} shown · {tasks.length} total</span></div>
    {error && <div className="form-error page-alert" role="alert">{error}</div>}

    {canCreate ? <div className="panel create-panel"><div><p className="eyebrow">Quick add</p><h3>Create a task</h3><p>Tasks start as Todo. Assign a workspace member and add a deadline when needed.</p></div><div className="form-row">
      <input className="workspace-input" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="Task name" />
      <input className="workspace-input" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="Description (optional)" />
      <select className="workspace-input" value={form.projectId} onChange={e => setForm({ ...form, projectId: e.target.value })}><option value="">Select project</option>{projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select>
      <select className="workspace-input" value={form.assigneeId} onChange={e => setForm({ ...form, assigneeId: e.target.value })}><option value="">Unassigned</option>{members.map(m => <option key={m.id} value={m.id}>{m.name} ({m.role})</option>)}</select>
      <select className="workspace-input" value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })}><option>Low</option><option>Medium</option><option>High</option><option>Critical</option></select>
      <input className="workspace-input" type="date" value={form.dueDate} onChange={e => setForm({ ...form, dueDate: e.target.value })} aria-label="Due date" />
      <button className="primary-button" onClick={addTask}><Plus size={15} /> Add task</button>
    </div></div> : <div className="panel permission-note"><strong>Member access</strong><span>You can update tasks assigned to you. Managers and admins assign work and review completed tasks.</span></div>}

    <div className="panel task-filters"><div className="filter-search"><Search size={15}/><input value={filters.search} onChange={e => setFilters({ ...filters, search: e.target.value })} placeholder="Search tasks, projects or people" /></div><select className="workspace-input" value={filters.projectId} onChange={e => setFilters({ ...filters, projectId: e.target.value })}><option value="">All projects</option>{projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select><select className="workspace-input" value={filters.assigneeId} onChange={e => setFilters({ ...filters, assigneeId: e.target.value })}><option value="">All assignees</option>{members.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}</select><select className="workspace-input" value={filters.status} onChange={e => setFilters({ ...filters, status: e.target.value })}><option value="">All statuses</option>{statuses.map(s => <option key={s}>{s}</option>)}</select><select className="workspace-input" value={filters.priority} onChange={e => setFilters({ ...filters, priority: e.target.value })}><option value="">All priorities</option>{["Low","Medium","High","Critical"].map(p => <option key={p}>{p}</option>)}</select></div>

    <div className="task-columns">{columns.map(status => <div className="task-column" key={status}><div className="column-heading"><span>{status}</span><strong>{filteredTasks.filter(t => t.status === status).length}</strong></div>{filteredTasks.filter(t => t.status === status).map(task => {
      const canChange = canManageAll || task.assignee?.id === user.id;
      return <div className="task-card panel" key={task.id}><div className="task-card-top"><span className="task-status-icon">{status === "Done" ? <CheckCircle2 size={15}/> : status === "In Progress" ? <Clock3 size={15}/> : <Circle size={15}/>}</span>{canManageAll && <button className="danger-button" onClick={() => remove(task.id)} aria-label={`Delete ${task.title}`}><Trash2 size={13}/></button>}</div><strong>{task.title}</strong>{task.description && <span className="task-description">{task.description}</span>}<span className="task-project">{task.projectName}</span><span>{task.assignee ? `Assigned to ${task.assignee.name}` : "Unassigned"}</span><span className="task-due-line"><CalendarDays size={12}/> {formatDate(task.dueDate)}</span><div className="task-card-footer"><select className="task-status-select" disabled={!canChange} value={task.status} onChange={e => changeStatus(task, e.target.value)} aria-label={`Status for ${task.title}`}>{statuses.map(s => <option key={s}>{s}</option>)}</select><em className={`priority ${task.priority.toLowerCase()}`}>{task.priority}</em></div>{status === "Review" && <small>Waiting for manager/admin review</small>}</div>;
    })}{!filteredTasks.filter(t => t.status === status).length && <div className="empty-state">No tasks here.</div>}</div>)}</div>
    <style>{`.task-filters{display:grid;grid-template-columns:minmax(220px,1.5fr) repeat(4,minmax(120px,1fr));gap:8px;margin:14px 0}.filter-search{display:flex;align-items:center;gap:8px;border:1px solid #dfe3e8;border-radius:8px;padding:0 11px;background:#fff}.filter-search input{border:0;outline:0;width:100%;padding:11px 0;color:#252936;background:transparent}.task-status-icon{display:flex;color:#5548c9}.task-description{font-size:12px!important;color:#777e89!important;line-height:1.4}.task-project{font-weight:700;color:#4f46a5!important}.task-due-line{display:flex!important;align-items:center;gap:4px;font-size:11px!important;color:#656c78!important}.task-card-footer{display:flex;align-items:center;justify-content:space-between;gap:7px;margin-top:4px}.task-status-select{font-size:11px;border:1px solid #dfe3e8;border-radius:7px;padding:5px 7px;background:#fff;color:#343944}.task-status-select:disabled{opacity:.7}.task-card small{color:#8a5b12}.@media(max-width:900px){.task-filters{grid-template-columns:1fr 1fr}.task-filters .filter-search{grid-column:1/-1}}@media(max-width:600px){.task-filters{grid-template-columns:1fr}.task-filters .filter-search{grid-column:auto}.form-row{grid-template-columns:1fr!important}.task-columns{grid-template-columns:1fr!important;overflow:visible!important}.task-column{min-width:0!important}}`}</style>
  </div>;
}
