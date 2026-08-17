import { useState } from "react";
import type { FormEvent } from "react";
import { ArrowRight, LockKeyhole, Mail, UserRound } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api";

export default function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  function update(field: keyof typeof form, value: string) { setForm(current => ({ ...current, [field]: value })); }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault(); setError(""); setLoading(true);
    try {
      const { data } = await api.post("/auth/register", form);
      localStorage.setItem("nexora_access_token", data.accessToken);
      localStorage.setItem("nexora_refresh_token", data.refreshToken);
      localStorage.setItem("nexora_token", data.accessToken);
      localStorage.setItem("nexora_user", JSON.stringify(data.user));
      navigate("/dashboard", { replace: true });
    } catch (err: any) { setError(err.response?.data?.message || "Unable to create your account."); }
    finally { setLoading(false); }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="auth-brand"><span className="brand-mark">N</span><strong>Nexora</strong></div>
        <p className="eyebrow">Start shipping</p>
        <h1>Create your workspace</h1>
        <p className="auth-subtitle">One account for projects, tasks, team collaboration and delivery analytics.</p>
        <form onSubmit={handleSubmit} className="auth-form">
          <label>Full name<div className="input-wrap"><input value={form.name} onChange={e => update("name", e.target.value)} placeholder="Your name" required /><UserRound size={16}/></div></label>
          <label>Work email<div className="input-wrap"><input type="email" value={form.email} onChange={e => update("email", e.target.value)} placeholder="you@company.com" required /><Mail size={16}/></div></label>
          <label>Password<div className="input-wrap"><input type="password" value={form.password} onChange={e => update("password", e.target.value)} placeholder="At least 8 characters" minLength={8} required /><LockKeyhole size={16}/></div></label>
          {error && <div className="form-error">{error}</div>}
          <button className="primary-button auth-submit" disabled={loading}>{loading ? "Creating workspace..." : <>Create account <ArrowRight size={16}/></>}</button>
        </form>
        <p className="auth-footer">Already have a Nexora workspace? <Link to="/login">Sign in</Link></p>
      </section>
    </main>
  );
}
