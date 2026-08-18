import { useState } from "react";
import type { FormEvent } from "react";
import { ArrowRight, LockKeyhole } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api";

function getApiError(error: unknown) {
  const err = error as { response?: { data?: { message?: string } } };
  if (err.response?.data?.message) return err.response.data.message;
  if (!err.response) return "We couldn't reach Nexora right now. Please check your connection and try again.";
  return "Unable to sign in. Please check your details and try again.";
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
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="login-title">
        <div className="auth-brand">
          <span className="brand-mark" aria-hidden="true">N</span>
          <strong>Nexora</strong>
        </div>
        <p className="eyebrow">Welcome back</p>
        <h1 id="login-title">Sign in to your workspace</h1>
        <p className="auth-subtitle">Keep your projects, people, and progress in one clear workspace.</p>

        <form onSubmit={handleSubmit} className="auth-form">
          <label>
            Work email
            <div className="input-wrap">
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" autoComplete="email" required />
            </div>
          </label>
          <label>
            Password
            <div className="input-wrap">
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Your password" autoComplete="current-password" required />
              <LockKeyhole size={16} aria-hidden="true" />
            </div>
          </label>
          {error && <div className="form-error" role="alert">{error}</div>}
          <button className="primary-button auth-submit" disabled={loading} type="submit">
            {loading ? "Signing in..." : <>Sign in <ArrowRight size={16} /></>}
          </button>
        </form>

        <p className="auth-footer">Don't have a Nexora workspace? <Link to="/register">Create one</Link></p>
      </section>
    </main>
  );
}
