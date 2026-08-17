import { useEffect, useState } from "react";
import { FolderKanban, Plus, Trash2 } from "lucide-react";
import api from "../api";

type Project = { id: number; name: string; description: string; status: string; progress: number };

export default function Projects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [form, setForm] = useState({ name: "", description: "" });
  const [loading, setLoading] = useState(false);
  const load = () => api.get("/projects").then(({ data }) => setProjects(data.projects));
  useEffect(() => { load(); }, []);

  async function createProject() {
    if (!form.name.trim()) return;
    setLoading(true);
    try { await api.post("/projects", form); setForm({ name: "", description: "" }); await load(); } finally { setLoading(false); }
  }

  async function removeProject(id: number) { await api.delete(`/projects/${id}`); load(); }

  return <div className="workspace-page">
    <div className="page-heading"><div><p className="eyebrow">Workspace</p><h2>Projects</h2><p>Organize initiatives and track delivery progress.</p></div></div>
    <div className="panel create-panel"><div><h3>Create a project</h3><p>Start a workspace initiative and add tasks to it.</p></div><div className="form-row"><input className="workspace-input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Project name" /><input className="workspace-input" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="Short description" /><button className="primary-button" onClick={createProject} disabled={loading}><Plus size={16} /> Create</button></div></div>
    <div className="card-grid">{projects.map(p => <div className="panel project-card" key={p.id}><div className="card-icon"><FolderKanban size={18}/></div><div className="card-title"><h3>{p.name}</h3><button className="danger-button" onClick={() => removeProject(p.id)} aria-label="Delete project"><Trash2 size={15}/></button></div><p>{p.description || "No description yet."}</p><div className="project-meta"><span>{p.status}</span><strong>{p.progress}%</strong></div><div className="progress"><div style={{ width: `${p.progress}%` }}/></div></div>)}</div>
    {!projects.length && <div className="panel empty-state large">No projects yet. Create one above to begin.</div>}
  </div>;
}
