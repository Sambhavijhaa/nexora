import { useEffect, useState } from "react";
import { Mail, ShieldCheck, UserRound, Users } from "lucide-react";
import api from "../api";

type Member = { id: number; name: string; email: string; role: string };

export default function Team() {
  const [members, setMembers] = useState<Member[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    api.get("/team").then(({ data }) => setMembers(data.members || [])).catch((err) => setError(err.response?.data?.message || "Could not load team."));
  }, []);

  return (
    <div className="workspace-page">
      <div className="page-heading">
        <div><p className="eyebrow">People</p><h2>Team</h2><p>Understand who is part of your workspace and the access level they hold.</p></div>
        <button className="primary-button" onClick={() => setError("Invitations will be connected to the workspace email service next.")}><Mail size={15}/> Invite member</button>
      </div>
      {error && <div className="form-error page-alert">{error}</div>}

      <div className="stats-grid">
        <div className="stat-card"><div className="stat-icon"><Users size={18}/></div><p>Workspace members</p><h3>{members.length}</h3></div>
        <div className="stat-card"><div className="stat-icon"><ShieldCheck size={18}/></div><p>Admins</p><h3>{members.filter(m => m.role === "Admin").length}</h3></div>
      </div>

      <div className="member-grid">
        {members.map(m => (
          <div className="panel member-card" key={m.id}>
            <div className="member-avatar"><UserRound size={17}/></div>
            <div><h3>{m.name}</h3><p>{m.email}</p></div>
            <span className="role-badge"><ShieldCheck size={12}/> {m.role}</span>
          </div>
        ))}
      </div>
      {!members.length && <div className="panel empty-state large">No team members found yet.</div>}
    </div>
  );
}
