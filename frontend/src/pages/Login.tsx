import { useState } from "react";
import type { FormEvent } from "react";
import { ArrowRight, LockKeyhole, Mail } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api";

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault(); setError(""); setLoading(true);
    try {
      const { data } = await api.post("/auth/login", { email, password });
      localStorage.setItem("nexora_access_token", data.accessToken);
      localStorage.setItem("nexora_refresh_token", data.refreshToken);
      localStorage.setItem("nexora_token", data.accessToken);
      localStorage.setItem("nexora_user", JSON.stringify(data.user));
      navigate("/dashboard", { replace: true });
    } catch (err: any) { setError(err.response?.data?.message || "Unable to sign in. Please try again."); }
    finally { setLoading(false); }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="auth-brand"><span className="brand-mark">N</span><strong>Nexora</strong></div>
        <p className="eyebrow">Welcome back</p>
        <h1>Sign in to your workspace</h1>
        <p className="auth-subtitle">Plan projects, coordinate your team and keep delivery moving from one focused workspace.</p>
        <form onSubmit={handleSubmit} className="auth-form">
          <label>Email<div className="input-wrap"><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" required /><Mail size={16}/></div></label>
          <label>Password<div className="input-wrap"><input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" required minLength={8} /><LockKeyhole size={16}/></div></label>
          {error && <div className="form-error">{error}</div>}
          <button className="primary-button auth-submit" disabled={loading}>{loading ? "Signing in..." : <>Sign in <ArrowRight size={16}/></>}</button>
        </form>
        <p className="auth-footer">Don't have a Nexora workspace? <Link to="/register">Create one</Link></p>
      </section>
    </main>
  );
}
