import { useEffect, useState } from "react";
import { CalendarDays, FolderKanban, Plus, Trash2, Users } from "lucide-react";
import { useNavigate } from "react-router-dom";
import api from "../api";

type Project = { id: number; name: string; description: string; status: string; progress: number; createdAt?: string };
type StoredUser = { role?: string };
function currentRole(): string { try { return (JSON.parse(localStorage.getItem("nexora_user") || "{}") as StoredUser).role || "Member"; } catch { return "Member"; } }

export default function Projects() {
  const navigate = useNavigate(); const [projects, setProjects] = useState<Project[]>([]); const [form, setForm] = useState({ name: "", description: "" }); const [loading, setLoading] = useState(false); const [error, setError] = useState(""); const role = currentRole(); const canManageProjects = role === "Admin" || role === "Manager";
  const load = () => api.get("/projects").then(({ data }) => setProjects(data.projects || [])).catch((err) => setError(err.response?.data?.message || "Could not load projects."));
  useEffect(() => { load(); }, []);
  async function createProject() { if (!form.name.trim() || !canManageProjects) return; setLoading(true); setError(""); try { await api.post("/projects", form); setForm({ name: "", description: "" }); await load(); } catch (err: any) { setError(err.response?.data?.message || "Could not create project."); } finally { setLoading(false); } }
  async function removeProject(id: number) { if (!canManageProjects) return; try { await api.delete(`/projects/${id}`); load(); } catch (err: any) { setError(err.response?.data?.message || "Could not delete project."); } }
  return <div className="workspace-page">
    <div className="page-heading"><div><p className="eyebrow">Workspace</p><h2>Projects</h2><p>Turn ideas into organized delivery with clear ownership and progress.</p></div>{canManageProjects && <button className="primary-button" onClick={() => document.getElementById("project-name")?.focus()}><Plus size={15}/> New project</button>}</div>
    {error && <div className="form-error page-alert" role="alert">{error}</div>}
    {canManageProjects ? <div className="panel create-panel"><div><p className="eyebrow">Create</p><h3>Start a new project</h3><p>Give your team a clear place to plan tasks, deadlines and progress.</p></div><div className="form-row"><input id="project-name" className="workspace-input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Project name"/><input className="workspace-input" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="Short description"/><button className="primary-button" onClick={createProject} disabled={loading}>{loading ? "Creating..." : <><Plus size={15}/> Create</>}</button></div></div> : <div className="panel permission-note"><strong>View only</strong><span>Your {role.toLowerCase()} access lets you work with existing projects without changing workspace projects.</span></div>}
    <div className="card-grid">{projects.map(p => <article className="panel project-card" key={p.id} onClick={() => navigate(`/projects/${p.id}`)} role="button" tabIndex={0} onKeyDown={e => { if (e.key === "Enter" || e.key === " ") navigate(`/projects/${p.id}`); }}><div className="card-icon"><FolderKanban size={18}/></div><div className="card-title"><h3>{p.name}</h3>{canManageProjects && <button className="danger-button" onClick={e => { e.stopPropagation(); removeProject(p.id); }} aria-label={`Delete ${p.name}`}><Trash2 size={14}/></button>}</div><p>{p.description || "No description yet. Add context so your team knows what success looks like."}</p><div className="project-meta"><span>{p.status}</span><strong>{p.progress}%</strong></div><div className="progress"><div style={{ width: `${p.progress}%` }}/></div><div className="project-meta" style={{ marginTop: 13 }}><span><Users size={12} style={{ verticalAlign: "-2px" }}/> Team workspace</span><span><CalendarDays size={12} style={{ verticalAlign: "-2px" }}/> Active</span></div><small className="project-open-hint">Open project →</small></article>)}</div>
    {!projects.length && <div className="panel empty-state large">No projects yet. {canManageProjects ? "Create your first project above and start building your delivery pipeline." : "Ask a manager or admin to create the first project."}</div>}
  </div>;
}
