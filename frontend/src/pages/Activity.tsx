import { useEffect, useState } from "react";
import { Activity as ActivityIcon, CheckCircle2, FolderPlus, ListTodo, Trash2, UserPlus } from "lucide-react";
import api from "../api";

type Item = { id: number; action: string; context: string; createdAt?: string };

function iconFor(action: string) {
  if (action.toLowerCase().includes("project")) return FolderPlus;
  if (action.toLowerCase().includes("task")) return ListTodo;
  if (action.toLowerCase().includes("member")) return UserPlus;
  return CheckCircle2;
}

export default function Activity() {
  const [items, setItems] = useState<Item[]>([]);
  const [error, setError] = useState("");
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    try {
      const storedUser = localStorage.getItem("nexora_user");
      const user = storedUser ? JSON.parse(storedUser) : null;
      setIsAdmin(user?.role === "Admin");
    } catch {
      setIsAdmin(false);
    }

    api.get("/activity")
      .then(({ data }) => setItems(data.activity || []))
      .catch((err) => setError(err.response?.data?.message || "Could not load activity."));
  }, []);

  const deleteActivity = async (id: number) => {
    if (!window.confirm("Delete this activity entry? This cannot be undone.")) return;
    setDeletingId(id);
    setError("");
    try {
      await api.delete(`/activity/${id}`);
      setItems((current) => current.filter((item) => item.id !== id));
    } catch (err: any) {
      setError(err.response?.data?.message || "Could not delete activity.");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="workspace-page">
      <div className="page-heading"><div><p className="eyebrow">Workspace timeline</p><h2>Activity</h2><p>Follow the actions shaping your projects and team.</p></div></div>
      {error && <div className="form-error page-alert">{error}</div>}
      <div className="panel">
        <div className="panel-header"><div><p className="eyebrow">Audit trail</p><h3>Recent activity</h3></div><ActivityIcon size={17} color="#8970ff" /></div>
        {items.length ? items.map((item) => {
          const Icon = iconFor(item.action);
          return (
            <div className="activity" key={item.id}>
              <div className="activity-avatar"><Icon size={14} /></div>
              <div style={{ flex: 1 }}>
                <strong>{item.action}</strong>
                <span>{item.context}{item.createdAt ? ` · ${new Date(item.createdAt).toLocaleString()}` : ""}</span>
              </div>
              {isAdmin && (
                <button
                  type="button"
                  onClick={() => deleteActivity(item.id)}
                  disabled={deletingId === item.id}
                  aria-label="Delete activity"
                  title="Delete activity"
                  style={{ border: 0, background: "transparent", cursor: deletingId === item.id ? "wait" : "pointer", padding: 8, opacity: deletingId === item.id ? 0.5 : 0.75 }}
                >
                  <Trash2 size={16} />
                </button>
              )}
            </div>
          );
        }) : <div className="empty-state">No activity yet. Create a project or task to start the timeline.</div>}
      </div>
    </div>
  );
}
