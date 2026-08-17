import { ArrowUpRight, CheckCircle2, Clock3, FolderKanban, Users } from "lucide-react";

const stats = [
  { title: "Active Projects", value: "12", change: "+18.2%", icon: FolderKanban },
  { title: "Tasks Completed", value: "284", change: "+12.5%", icon: CheckCircle2 },
  { title: "Team Members", value: "24", change: "+4.3%", icon: Users },
  { title: "Hours Tracked", value: "1,248", change: "+8.7%", icon: Clock3 },
];

const projects = [
  { name: "Website Redesign", detail: "12 of 18 tasks completed", progress: 67 },
  { name: "Mobile Application", detail: "24 of 40 tasks completed", progress: 60 },
  { name: "Marketing Campaign", detail: "8 of 10 tasks completed", progress: 80 },
];

export default function Dashboard() {
  return (
    <div className="dashboard">
      <div className="welcome-section">
        <div>
          <p className="eyebrow">Overview</p>
          <h2>Good afternoon, Sambhavi <span aria-hidden="true">👋</span></h2>
          <p>Here's what's happening across your workspace today.</p>
        </div>
        <button className="primary-button">+ New Project</button>
      </div>

      <div className="stats-grid">
        {stats.map(({ title, value, change, icon: Icon }) => (
          <div className="stat-card" key={title}>
            <div className="stat-top">
              <div className="stat-icon"><Icon size={19} /></div>
              <span className="stat-change">{change}<ArrowUpRight size={13} /></span>
            </div>
            <p>{title}</p>
            <h3>{value}</h3>
          </div>
        ))}
      </div>

      <div className="dashboard-grid">
        <div className="panel">
          <div className="panel-header">
            <div><p className="eyebrow">Projects</p><h3>Project progress</h3></div>
            <button className="text-button">View all</button>
          </div>
          {projects.map((project) => (
            <div className="project-block" key={project.name}>
              <div className="project-row">
                <div><strong>{project.name}</strong><span>{project.detail}</span></div>
                <strong>{project.progress}%</strong>
              </div>
              <div className="progress"><div style={{ width: `${project.progress}%` }} /></div>
            </div>
          ))}
        </div>

        <div className="panel">
          <div className="panel-header"><div><p className="eyebrow">Activity</p><h3>Recent activity</h3></div></div>
          <div className="activity"><div className="activity-avatar">SJ</div><div><strong>Sambhavi completed a task</strong><span>Website Redesign · 12 min ago</span></div></div>
          <div className="activity"><div className="activity-avatar">AK</div><div><strong>Alex joined the workspace</strong><span>Team · 42 min ago</span></div></div>
          <div className="activity"><div className="activity-avatar">RM</div><div><strong>Riya created a project</strong><span>Mobile Application · 2 hrs ago</span></div></div>
        </div>
      </div>
    </div>
  );
}
