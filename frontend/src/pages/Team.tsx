import { useEffect, useState } from "react";
import { Mail, ShieldCheck, Trash2, UserRound, Users } from "lucide-react";
import api from "../api";

type Member = { id: number; name: string; email: string; role: string };

export default function Team() {
  const [members, setMembers] = useState<Member[]>([]);
  const [workspaceRole, setWorkspaceRole] = useState("");
  const [error, setError] = useState("");

  const canManage = workspaceRole === "Admin" || workspaceRole === "Manager";
  const canChangeRoles = workspaceRole === "Admin";

  const load = async () => {
    try {
      const [{ data: teamData }, { data: workspaceData }] = await Promise.all([
        api.get("/team"),
        api.get("/workspace"),
      ]);
      setMembers(teamData.members || []);
      setWorkspaceRole(workspaceData.workspace?.role || "");
    } catch (err: any) {
      setError(err.response?.data?.message || "Could not load team.");
    }
  };

  useEffect(() => { load(); }, []);

  async function changeRole(member: Member, role: string) {
    if (!canChangeRoles) return;
    setError("");
    try {
      await api.patch(`/team/${member.id}`, { role });
      await load();
    } catch (err: any) {
      setError(err.response?.data?.message || "Could not update member role.");
    }
  }

  async function removeMember(member: Member) {
    if (!canChangeRoles) return;
    if (!window.confirm(`Remove ${member.name} from this workspace?`)) return;
    setError("");
    try {
      await api.delete(`/team/${member.id}`);
      await load();
    } catch (err: any) {
      setError(err.response?.data?.message || "Could not remove member.");
    }
  }

  return (
    <div className="workspace-page">
      <div className="page-heading">
        <div><p className="eyebrow">People</p><h2>Team</h2><p>See everyone in your workspace and the access level they hold.</p></div>
        {canManage && <button className="primary-button" onClick={() => setError("The invitation endpoint is ready; connect your email provider when you want live invitations.")}><Mail size={15}/> Invite member</button>}
      </div>
      {error && <div className="form-error page-alert" role="alert">{error}</div>}

      <div className="stats-grid">
        <div className="stat-card"><div className="stat-icon"><Users size={18}/></div><p>Workspace members</p><h3>{members.length}</h3></div>
        <div className="stat-card"><div className="stat-icon"><ShieldCheck size={18}/></div><p>Admins</p><h3>{members.filter(m => m.role === "Admin").length}</h3></div>
      </div>

      <div className="member-grid">
        {members.map(m => (
          <div className="panel member-card" key={m.id}>
            <div className="member-avatar"><UserRound size={17}/></div>
            <div><h3>{m.name}</h3><p>{m.email}</p></div>
            {canChangeRoles ? (
              <div className="member-actions">
                <select className="role-select" value={m.role} onChange={(e) => changeRole(m, e.target.value)} aria-label={`Role for ${m.name}`}>
                  <option>Admin</option><option>Manager</option><option>Member</option><option>Viewer</option>
                </select>
                <button className="danger-button" onClick={() => removeMember(m)} aria-label={`Remove ${m.name}`}><Trash2 size={14}/></button>
              </div>
            ) : <span className="role-badge"><ShieldCheck size={12}/> {m.role}</span>}
          </div>
        ))}
      </div>
      {!members.length && <div className="panel empty-state large">No team members found yet.</div>}
    </div>
  );
}
