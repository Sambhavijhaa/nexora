import { useEffect, useState } from "react";
import { Mail, ShieldCheck, Trash2, UserRound, Users, X } from "lucide-react";
import api from "../api";

type Member = { id: number; name: string; email: string; role: string };

export default function Team() {
  const [members, setMembers] = useState<Member[]>([]);
  const [workspaceRole, setWorkspaceRole] = useState("");
  const [error, setError] = useState("");
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("Member");
  const [inviteLoading, setInviteLoading] = useState(false);
  const [inviteSuccess, setInviteSuccess] = useState("");

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

  async function inviteMember() {
    if (!inviteEmail.trim()) {
      setError("Enter the email address of the person you want to invite.");
      return;
    }
    setInviteLoading(true);
    setError("");
    setInviteSuccess("");
    try {
      await api.post("/team/invite", {
        email: inviteEmail.trim(),
        role: inviteRole,
      });
      setInviteSuccess(`Invitation sent to ${inviteEmail.trim()}.`);
      setInviteEmail("");
      setInviteRole("Member");
      await load();
    } catch (err: any) {
      setError(err.response?.data?.message || "Could not send invitation.");
    } finally {
      setInviteLoading(false);
    }
  }

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
        {canManage && <button className="primary-button" onClick={() => { setInviteOpen(true); setError(""); setInviteSuccess(""); }}><Mail size={15}/> Invite member</button>}
      </div>
      {error && <div className="form-error page-alert" role="alert">{error}</div>}
      {inviteSuccess && <div className="page-alert" role="status">{inviteSuccess}</div>}

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

      {inviteOpen && (
        <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setInviteOpen(false); }}>
          <div className="invite-modal" role="dialog" aria-modal="true" aria-labelledby="invite-title">
            <div className="invite-modal-header"><div><p className="eyebrow">Workspace</p><h2 id="invite-title">Invite member</h2></div><button className="icon-button" type="button" onClick={() => setInviteOpen(false)} aria-label="Close invitation"><X size={18}/></button></div>
            <p className="invite-help">Invite someone to join this workspace. They will receive an invitation and get the selected access level after accepting.</p>
            <label className="field-label" htmlFor="invite-email">Email address</label>
            <input id="invite-email" className="text-input" type="email" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} placeholder="name@example.com" autoComplete="email" />
            <label className="field-label" htmlFor="invite-role">Role</label>
            <select id="invite-role" className="text-input" value={inviteRole} onChange={(e) => setInviteRole(e.target.value)}>
              <option value="Manager">Manager</option>
              <option value="Member">Member</option>
              <option value="Viewer">Viewer</option>
            </select>
            <div className="invite-actions"><button className="secondary-button" type="button" onClick={() => setInviteOpen(false)}>Cancel</button><button className="primary-button" type="button" onClick={inviteMember} disabled={inviteLoading}>{inviteLoading ? "Sending..." : "Send invitation"}</button></div>
          </div>
        </div>
      )}

      <style>{`
        .modal-backdrop{position:fixed;inset:0;z-index:1200;display:flex;align-items:center;justify-content:center;padding:20px;background:rgba(17,24,39,.32)}
        .invite-modal{width:min(100%,460px);box-sizing:border-box;background:#fff;color:#171a21;border:1px solid #e1e4e8;border-radius:14px;padding:24px;box-shadow:0 24px 70px rgba(17,24,39,.18)}
        .invite-modal-header{display:flex;align-items:flex-start;justify-content:space-between;gap:15px}.invite-modal-header h2{margin:3px 0 0;color:#171a21}.invite-help{margin:14px 0 20px;color:#626975;line-height:1.5;font-size:14px}.field-label{display:block;margin:14px 0 7px;color:#343944;font-size:13px;font-weight:700}.text-input{width:100%;box-sizing:border-box;padding:11px 12px;border:1px solid #d7dbe1;border-radius:8px;background:#fff;color:#171a21;font:inherit;outline:none}.text-input:focus{border-color:#5548c9;box-shadow:0 0 0 3px rgba(85,72,201,.12)}.invite-actions{display:flex;justify-content:flex-end;gap:10px;margin-top:24px}.secondary-button{padding:10px 14px;border:1px solid #d7dbe1;border-radius:8px;background:#fff;color:#343944;font-weight:700;cursor:pointer}.invite-actions .primary-button{border:0}.invite-actions button:disabled{opacity:.6;cursor:not-allowed}@media(max-width:560px){.invite-modal{padding:20px}.invite-actions{flex-direction:column-reverse}.invite-actions button{width:100%}}
      `}</style>
    </div>
  );
}
