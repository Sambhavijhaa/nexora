import { useEffect, useState } from "react";
import { ShieldCheck, UserRound } from "lucide-react";
import api from "../api";

type Member = { id: number; name: string; email: string; role: string };
export default function Team() {
  const [members, setMembers] = useState<Member[]>([]);
  useEffect(() => { api.get("/team").then(({ data }) => setMembers(data.members)); }, []);
  return <div className="workspace-page"><div className="page-heading"><div><p className="eyebrow">People</p><h2>Team</h2><p>See the people who have access to the Nexora workspace.</p></div></div><div className="member-grid">{members.map(m => <div className="panel member-card" key={m.id}><div className="member-avatar"><UserRound size={18}/></div><div><h3>{m.name}</h3><p>{m.email}</p></div><span className="role-badge"><ShieldCheck size={13}/> {m.role}</span></div>)}</div>{!members.length && <div className="panel empty-state large">No team members found.</div>}</div>;
}
