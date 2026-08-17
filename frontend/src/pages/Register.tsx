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

  function update(field: keyof typeof form, value: string) { setForm((current) => ({ ...current, [field]: value })); }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await api.post("/auth/register", form);
      localStorage.setItem("nexora_token", data.token);
      localStorage.setItem("nexora_user", JSON.stringify(data.user));
      navigate("/dashboard", { replace: true });
    } catch (err: any) {
      setError(err.response?.data?.message || "Unable to create your account.");
    } finally { setLoading(false); }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="auth-brand"><span className="brand-mark">N</span><strong>Nexora</strong></div>
        <p className="eyebrow">Get started</p>
        <h1>Create your workspace</h1>
        <p className="auth-subtitle">Start organizing projects and collaborating with your team in Nexora.</p>
        <form onSubmit={handleSubmit} className="auth-form">
          <label>Full name<div className="input-wrap"><input value={form.name} onChange={(e) => update("name", e.target.value)} placeholder="Sambhavi Jha" required /><UserRound size={17} /></div></label>
          <label>Email<div className="input-wrap"><input type="email" value={form.email} onChange={(e) => update("email", e.target.value)} placeholder="you@company.com" required /><Mail size={17} /></div></label>
          <label>Password<div className="input-wrap"><input type="password" value={form.password} onChange={(e) => update("password", e.target.value)} placeholder="At least 8 characters" minLength={8} required /><LockKeyhole size={17} /></div></label>
          {error && <div className="form-error">{error}</div>}
          <button className="primary-button auth-submit" disabled={loading}>{loading ? "Creating workspace..." : <>Create account <ArrowRight size={17} /></>}</button>
        </form>
        <p className="auth-footer">Already have an account? <Link to="/login">Sign in</Link></p>
      </section>
    </main>
  );
}
