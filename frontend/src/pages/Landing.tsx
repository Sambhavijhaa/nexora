import { ArrowRight, BarChart3, CheckCircle2, FolderKanban, Users } from "lucide-react";
import { Link } from "react-router-dom";

const features = [
  { icon: FolderKanban, title: "Projects", text: "Plan work, track delivery and keep every project moving." },
  { icon: CheckCircle2, title: "Tasks", text: "Assign owners, priorities and statuses from one focused board." },
  { icon: Users, title: "Team", text: "Bring your people together with clear roles and shared context." },
  { icon: BarChart3, title: "Analytics", text: "Turn everyday work into simple, useful delivery insights." },
];

export default function Landing() {
  return (
    <main className="landing-page">
      <nav className="landing-nav">
        <div className="brand landing-brand"><span className="brand-mark">N</span><span>Nexora</span></div>
        <div className="landing-actions">
          <Link to="/login" className="landing-login">Sign in</Link>
          <Link to="/register" className="primary-button landing-cta">Get started <ArrowRight size={15} /></Link>
        </div>
      </nav>

      <section className="landing-hero">
        <p className="eyebrow">Project management for modern teams</p>
        <h1>Work clearly.<br /><span>Ship confidently.</span></h1>
        <p>Projects, tasks, people and delivery insights in one calm workspace built for teams that want less noise and more progress.</p>
        <div className="landing-hero-actions">
          <Link to="/register" className="primary-button">Create your workspace <ArrowRight size={16} /></Link>
          <Link to="/login" className="landing-secondary">Sign in</Link>
        </div>

        <div className="landing-preview" aria-label="Nexora dashboard preview">
          <div className="preview-sidebar"><div className="preview-logo">N</div><span /> <span /><span /><span /><span /></div>
          <div className="preview-main">
            <div className="preview-top"><div><small>Workspace overview</small><strong>Good morning 👋</strong></div><i /></div>
            <div className="preview-stats"><div /><div /><div /><div /></div>
            <div className="preview-grid"><div className="preview-chart"><small>Task completion</small><div className="preview-bars">{[32,48,40,62,55,76,67].map((height) => <b key={height} style={{ height: `${height}%` }} />)}</div></div><div className="preview-list"><small>Recent activity</small><p /><p /><p /><p /></div></div>
          </div>
        </div>
      </section>

      <section className="landing-features">
        {features.map(({ icon: Icon, title, text }) => <article key={title}><div><Icon size={18} /></div><h3>{title}</h3><p>{text}</p></article>)}
      </section>

      <footer className="landing-footer"><span>© {new Date().getFullYear()} Nexora</span><span>Work smarter. Ship faster.</span></footer>
    </main>
  );
}
