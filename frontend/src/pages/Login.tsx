import { useState } from "react";
import type { FormEvent } from "react";
import { ArrowRight, LockKeyhole } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api";

function getApiError(error: unknown) {
  const err = error as { code?: string; response?: { data?: { message?: string } } };
  if (err.response?.data?.message) return err.response.data.message;
  if (err.code === "ECONNABORTED") return "Nexora is taking too long to respond. Please try again.";
  return "We couldn't reach Nexora right now. Please check your connection and try again.";
}

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await api.post("/auth/login", { email, password });
      if (!data.accessToken || !data.refreshToken || !data.user) {
        throw new Error("The server returned an incomplete login response.");
      }

      localStorage.setItem("nexora_access_token", data.accessToken);
      localStorage.setItem("nexora_refresh_token", data.refreshToken);
      localStorage.setItem("nexora_token", data.accessToken);
      localStorage.setItem("nexora_user", JSON.stringify(data.user));

      // If the user arrived through an invitation, accept it and immediately
      // make that workspace the active workspace.
      const inviteToken = localStorage.getItem("nexora_invitation_token");
      if (inviteToken) {
        try {
          const accepted = await api.post("/team/accept", { token: inviteToken });
          const invitedWorkspace = accepted.data?.workspace;
          if (invitedWorkspace?.id) {
            localStorage.setItem("nexora_workspace_id", String(invitedWorkspace.id));
            localStorage.setItem("nexora_workspace_role", invitedWorkspace.role || "Member");
          }
          localStorage.removeItem("nexora_invitation_token");
        } catch (inviteError: any) {
          setError(inviteError.response?.data?.message || "Signed in, but the invitation could not be accepted.");
          return;
        }
      } else if (data.workspace?.id) {
        localStorage.setItem("nexora_workspace_id", String(data.workspace.id));
        localStorage.setItem("nexora_workspace_role", data.workspace.role || "Member");
      }

      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setLoading(false);
    }
  }

  return <main className="auth-page"><section className="auth-card" aria-labelledby="login-title"><div className="auth-brand"><span className="brand-mark" aria-hidden="true">N</span><strong>Nexora</strong></div><p className="eyebrow">Welcome back</p><h1 id="login-title">Sign in to your workspace</h1><p className="auth-subtitle">Keep your projects, people, and progress in one clear workspace.</p><form onSubmit={handleSubmit} className="auth-form"><label>Work email<div className="input-wrap"><input type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@company.com" autoComplete="email" required/></div></label><label>Password<div className="input-wrap"><input type="password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="Your password" autoComplete="current-password" required/><LockKeyhole size={16}/></div></label>{error&&<div className="form-error" role="alert">{error}</div>}<button className="primary-button auth-submit" disabled={loading} type="submit">{loading?"Signing in...":<>Sign in <ArrowRight size={16}/></>}</button></form><p className="auth-footer">Don't have a Nexora workspace? <Link to="/register">Create one</Link></p></section></main>;
}
