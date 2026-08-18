import { useState } from "react";
import type { FormEvent } from "react";
import { ArrowRight, Eye, EyeOff, Mail, UserRound } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api";

function getApiError(error: unknown, fallback: string) {
  const err = error as { response?: { data?: { message?: string } } };
  if (err.response?.data?.message) return err.response.data.message;
  if (!err.response) return "We couldn't reach Nexora right now. Please check your connection and try again.";
  return fallback;
}

export default function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  function update(field: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await api.post("/auth/register", form);
      if (!data.accessToken || !data.refreshToken || !data.user) {
        throw new Error("The server returned an incomplete registration response.");
      }
      localStorage.setItem("nexora_access_token", data.accessToken);
      localStorage.setItem("nexora_refresh_token", data.refreshToken);
      localStorage.setItem("nexora_token", data.accessToken);
      localStorage.setItem("nexora_user", JSON.stringify(data.user));
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(getApiError(err, "Unable to create your account. Please try again."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="register-title">
        <div className="auth-brand">
          <strong>Nexora</strong>
        </div>
        <p className="eyebrow">Get started</p>
        <h1 id="register-title">Create your workspace</h1>
        <p className="auth-subtitle">Keep your projects, people, and progress in one clear workspace.</p>

        <form onSubmit={handleSubmit} className="auth-form">
          <label>
            Full name
            <div className="input-wrap">
              <input value={form.name} onChange={(e) => update("name", e.target.value)} placeholder="Your name" autoComplete="name" required maxLength={100} />
              <UserRound size={16} aria-hidden="true" />
            </div>
          </label>
          <label>
            Work email
            <div className="input-wrap">
              <input type="email" value={form.email} onChange={(e) => update("email", e.target.value)} placeholder="you@company.com" autoComplete="email" required />
              <Mail size={16} aria-hidden="true" />
            </div>
          </label>
          <label>
            Password
            <div className="input-wrap" style={{ position: "relative" }}>
              <input
                type={showPassword ? "text" : "password"}
                value={form.password}
                onChange={(e) => update("password", e.target.value)}
                placeholder="At least 8 characters"
                autoComplete="new-password"
                minLength={8}
                required
                style={{ paddingRight: "44px" }}
              />
              <button
                type="button"
                onClick={() => setShowPassword((visible) => !visible)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                style={{
                  all: "unset",
                  position: "absolute",
                  right: "8px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  width: "32px",
                  height: "32px",
                  display: "grid",
                  placeItems: "center",
                  boxSizing: "border-box",
                  cursor: "pointer",
                  color: "#71809a",
                }}
              >
                {showPassword ? <EyeOff size={16} aria-hidden="true" /> : <Eye size={16} aria-hidden="true" />}
              </button>
            </div>
          </label>
          {error && <div className="form-error" role="alert">{error}</div>}
          <button className="primary-button auth-submit" disabled={loading} type="submit">
            {loading ? "Creating account..." : <>Create account <ArrowRight size={16} /></>}
          </button>
        </form>

        <p className="auth-footer">Already have a Nexora workspace? <Link to="/login">Sign in</Link></p>
      </section>
    </main>
  );
}
