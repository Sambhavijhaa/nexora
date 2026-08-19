import { useEffect, useState } from "react";
import { CheckCheck, Bell } from "lucide-react";
import api from "../api";

type NotificationItem = { id: number; title: string; message: string; kind: string; read: boolean; createdAt?: string | null };

export default function Notifications() {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const { data } = await api.get("/notifications");
      setItems(data.notifications || []);
    } finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, []);

  async function markRead(id: number) {
    await api.patch(`/notifications/${id}/read`);
    setItems((current) => current.map((item) => item.id === id ? { ...item, read: true } : item));
  }

  async function markAll() {
    await api.post("/notifications/read-all");
    setItems((current) => current.map((item) => ({ ...item, read: true })));
  }

  return (
    <div className="simple-page">
      <div className="page-heading-row">
        <div><p className="eyebrow">Inbox</p><h1>Notifications</h1><p>Important updates from your workspace.</p></div>
        <button className="button button-secondary" onClick={() => void markAll()}><CheckCheck size={16} /> Mark all read</button>
      </div>
      <div className="simple-list">
        {loading ? <div className="empty-state">Loading notifications…</div> : items.length === 0 ? <div className="empty-state"><Bell size={22} /><span>You're all caught up.</span></div> : items.map((item) => (
          <button key={item.id} className={`simple-list-item ${item.read ? "read" : "unread"}`} onClick={() => !item.read && void markRead(item.id)}>
            <span className="simple-icon"><Bell size={17} /></span>
            <span className="simple-list-copy"><strong>{item.title}</strong><span>{item.message}</span></span>
            {!item.read && <span className="status-dot" aria-label="Unread" />}
          </button>
        ))}
      </div>
    </div>
  );
}
