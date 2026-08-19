import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, Circle, Clock3, Plus, Trash2 } from "lucide-react";
import api from "../api";

type Project = { id: number; name: string };
type Member = { id: number; name: string; email: string; role: string };
type Task = {
  id: number;
  title: string;
  status: string;
  priority: string;
  projectId: number;
  projectName: string;
  assignee?: { id: number; name: string; email: string; role: string } | null;
};
type StoredUser = { id?: number; role?: string };

const columns = ["Todo", "In Progress", "Review", "Done"];

function currentUser(): StoredUser {
  try {
    return JSON.parse(localStorage.getItem("nexora_user") || "{}") as StoredUser;
  } catch {
    return {};
  }
}

export default function Tasks() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [form, setForm] = useState({ title: "", projectId: "", assigneeId: "", priority: "Medium" });
  const [error, setError] = useState("");
  const user = currentUser();
  const canCreate = user.role === "Admin" || user.role === "Manager";
  const canManageAll = user.role === "Admin" || user.role === "Manager";

  const load = async () => {
    try {
      const requests: Promise<any>[] = [api.get("/tasks"), api.get("/projects")];
      if (canCreate) requests.push(api.get("/team"));
      const [t, p, team] = await Promise.all(requests);
      setTasks(t.data.tasks || []);
      setProjects(p.data.projects || []);
      if (team) setMembers(team.data.members || []);
      if (!form.projectId && p.data.projects?.[0]) {
        setForm(f => ({ ...f, projectId: String(p.data.projects[0].id) }));
      }
    } catch (err: any) {
      setError(err.response?.data?.message || "Could not load tasks.");
    }
  };

  useEffect(() => { load(); }, []);

  async function addTask() {
    if (!canCreate || !form.title.trim() || !form.projectId) return;
    try {
      await api.post("/tasks", {
        title: form.title.trim(),
        projectId: Number(form.projectId),
        priority: form.priority,
        assigneeId: form.assigneeId ? Number(form.assigneeId) : null,
        status: "Todo",
      });
      setForm(f => ({ ...f, title: "", assigneeId: "" }));
      await load();
    } catch (err: any) {
      setError(err.response?.data?.message || "Could not create task.");
    }
  }

  async function changeStatus(task: Task) {
    const isAssignee = task.assignee?.id === user.id;
    const canChange = canManageAll || isAssignee;
    if (!canChange) return;

    let next: string | null = null;
    if (canManageAll) {
      next = task.status === "Todo"
        ? "In Progress"
        : task.status === "In Progress"
          ? "Review"
          : task.status === "Review"
            ? "Done"
            : null;
    } else if (isAssignee) {
      next = task.status === "Todo"
        ? "In Progress"
        : task.status === "In Progress"
          ? "Review"
          : null;
    }

    if (!next) return;
    try {
      await api.patch(`/tasks/${task.id}`, { status: next });
      await load();
    } catch (err: any) {
      setError(err.response?.data?.message || "Could not update task.");
    }
  }

  async function remove(id: number) {
    if (!canManageAll) return;
    try {
      await api.delete(`/tasks/${id}`);
      await load();
    } catch (err: any) {
      setError(err.response?.data?.message || "Could not delete task.");
    }
  }

  const counts = useMemo(
    () => columns.map(status => ({ status, count: tasks.filter(t => t.status === status).length })),
    [tasks]
  );

  return (
    <div className="workspace-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Execution</p>
          <h2>Tasks</h2>
          <p>Assign work, track progress, and move tasks from Todo to Done.</p>
        </div>
        <span className="role-badge">{tasks.length} total tasks</span>
      </div>

      {error && <div className="form-error page-alert" role="alert">{error}</div>}

      {canCreate ? (
        <div className="panel create-panel">
          <div>
            <p className="eyebrow">Quick add</p>
            <h3>Create a task</h3>
            <p>Choose the project, assign a team member, and set the priority. New tasks start as Todo.</p>
          </div>
          <div className="form-row">
            <input
              className="workspace-input"
              value={form.title}
              onChange={e => setForm({ ...form, title: e.target.value })}
              placeholder="e.g. Implement JWT authentication"
            />
            <select className="workspace-input" value={form.projectId} onChange={e => setForm({ ...form, projectId: e.target.value })}>
              <option value="">Select project</option>
              {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <select className="workspace-input" value={form.assigneeId} onChange={e => setForm({ ...form, assigneeId: e.target.value })}>
              <option value="">Unassigned</option>
              {members.map(member => <option key={member.id} value={member.id}>{member.name} ({member.role})</option>)}
            </select>
            <select className="workspace-input" value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })}>
              <option>Low</option>
              <option>Medium</option>
              <option>High</option>
              <option>Critical</option>
            </select>
            <button className="primary-button" onClick={addTask}><Plus size={15} /> Add task</button>
          </div>
        </div>
      ) : (
        <div className="panel permission-note">
          <strong>Member access</strong>
          <span>You can view the board and update tasks assigned to you. Managers and admins assign work and approve completed tasks.</span>
        </div>
      )}

      <div className="task-columns">
        {counts.map(({ status, count }) => (
          <div className="task-column" key={status}>
            <div className="column-heading"><span>{status}</span><strong>{count}</strong></div>
            {tasks.filter(t => t.status === status).map(task => {
              const isAssignee = task.assignee?.id === user.id;
              const canChange = canManageAll || isAssignee;
              const canMove = canManageAll
                ? status !== "Done"
                : isAssignee && status !== "Review" && status !== "Done";

              return (
                <div className="task-card panel" key={task.id}>
                  <div className="task-card-top">
                    <button
                      className="task-status"
                      onClick={() => changeStatus(task)}
                      disabled={!canChange || !canMove}
                      aria-label={canMove ? `Move ${task.title}` : `${task.title} status cannot be changed here`}
                      title={canMove ? "Move to next status" : "No status change available"}
                    >
                      {status === "Done" ? <CheckCircle2 size={15} /> : status === "In Progress" ? <Clock3 size={15} /> : <Circle size={15} />}
                    </button>
                    {canManageAll && <button className="danger-button" onClick={() => remove(task.id)} aria-label={`Delete ${task.title}`}><Trash2 size={13} /></button>}
                  </div>
                  <strong>{task.title}</strong>
                  <span>{task.projectName}</span>
                  <span>{task.assignee ? `Assigned to ${task.assignee.name}` : "Unassigned"}</span>
                  <em className={`priority ${task.priority.toLowerCase()}`}>{task.priority}</em>
                  {status === "Review" && <small>Waiting for manager/admin review</small>}
                </div>
              );
            })}
            {!tasks.filter(t => t.status === status).length && <div className="empty-state">No tasks here yet.</div>}
          </div>
        ))}
      </div>
    </div>
  );
}
