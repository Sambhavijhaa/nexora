import { Link } from "react-router-dom";

const page: React.CSSProperties = { minHeight: "100svh", background: "#f7f8fa", color: "#11141b", display: "flex", flexDirection: "column", overflowX: "hidden" };
const nav: React.CSSProperties = { minHeight: 68, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 18px", background: "#fff", borderBottom: "1px solid #e1e4e8" };
const brand: React.CSSProperties = { color: "#11141b", textDecoration: "none", fontSize: 20, fontWeight: 800, display: "flex", alignItems: "center", gap: 9 };

export default function Landing() {
  return (
    <main style={page}>
      <nav style={nav}>
        <Link to="/" style={brand}><span style={{ width: 32, height: 32, borderRadius: 8, display: "grid", placeItems: "center", background: "#5548c9", color: "#fff", fontSize: 14 }}>N</span>Nexora</Link>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <Link to="/login" style={{ color: "#20242d", textDecoration: "none", fontSize: 14, fontWeight: 700, padding: "9px 10px" }}>Sign in</Link>
          <Link to="/register" style={{ color: "#fff", background: "#5548c9", textDecoration: "none", fontSize: 14, fontWeight: 700, padding: "10px 12px", borderRadius: 8 }}>Create account</Link>
        </div>
      </nav>
      <section style={{ flex: 1, width: "100%", maxWidth: 1100, margin: "0 auto", padding: "clamp(70px,12vh,130px) 22px 60px" }}>
        <div style={{ maxWidth: 700 }}>
          <p style={{ margin: "0 0 14px", color: "#5548c9", fontSize: 12, fontWeight: 800, letterSpacing: ".12em", textTransform: "uppercase" }}>Nexora workspace</p>
          <h1 style={{ margin: 0, color: "#11141b", fontSize: "clamp(42px,8vw,76px)", lineHeight: 1.03, letterSpacing: "-.055em", fontWeight: 800 }}>Move work forward,<br />together<span style={{ color: "#5548c9" }}>.</span></h1>
          <p style={{ margin: "22px 0 0", maxWidth: 500, color: "#4f5663", fontSize: "clamp(16px,2vw,19px)", lineHeight: 1.6 }}>Projects, people, and progress in one place.</p>
        </div>
      </section>
      <footer style={{ padding: "12px 18px", color: "#6b7280", background: "#fff", borderTop: "1px solid #e1e4e8", fontSize: 11, textAlign: "center" }}>© 2026 Nexora</footer>
    </main>
  );
}
