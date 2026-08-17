import { LogOut, ShieldCheck, UserRound } from "lucide-react";
import { useNavigate } from "react-router-dom";
import api from "../api";

export default function Settings() {
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem("nexora_user") || "{}") as {
    name?: string;
    email?: string;
    role?: string;
  };

  async function logout() {
    try {
      await api.post("/auth/logout", {});
    } catch {
      // Tokens are still removed locally if the API is unavailable.
    }

    localStorage.removeItem("nexora_access_token");
    localStorage.removeItem("nexora_refresh_token");
    localStorage.removeItem("nexora_token");
    localStorage.removeItem("nexora_user");
    navigate("/login", { replace: true });
  }

  return (
    <div className="workspace-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Account</p>
          <h2>Settings</h2>
          <p>Manage your workspace identity and session.</p>
        </div>
      </div>

      <div className="settings-grid">
        <div className="panel settings-card">
          <div className="settings-icon">
            <UserRound size={18} />
          </div>
          <div>
            <h3>Profile</h3>
            <p>
              Signed in as <strong>{user.name || "User"}</strong>
            </p>
            <p>{user.email || ""}</p>
          </div>
          <span className="role-badge">
            <ShieldCheck size={13} /> {user.role || "Member"}
          </span>
        </div>

        <div className="panel settings-card">
          <div className="settings-icon">
            <ShieldCheck size={18} />
          </div>
          <div>
            <h3>Security</h3>
            <p>
              JWT access tokens expire automatically and refresh tokens keep your
              session active.
            </p>
          </div>
        </div>
      </div>

      <button className="danger-action" onClick={logout}>
        <LogOut size={16} /> Sign out of Nexora
      </button>
    </div>
  );
}
