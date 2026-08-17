import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

export default function Landing() {
  return (
    <main className="landing-page">
      <nav className="landing-nav">
        <Link to="/" className="brand landing-brand" aria-label="Nexora home">
          <span className="brand-mark">N</span><span>Nexora</span>
        </Link>
        <div className="landing-actions">
          <Link to="/login" className="landing-login">Sign in</Link>
          <Link to="/register" className="primary-button landing-cta">Get started <ArrowRight size={15} /></Link>
        </div>
      </nav>

      <section className="landing-hero">
        <p className="eyebrow">A calmer way to run your team</p>
        <h1>Bring your work<br /><span>into focus.</span></h1>
        <p className="landing-lead">Nexora gives modern teams one clear place to organize work, stay aligned, and keep projects moving.</p>
        <div className="landing-hero-actions">
          <Link to="/register" className="primary-button">Start for free <ArrowRight size={16} /></Link>
          <Link to="/login" className="landing-secondary">Sign in</Link>
        </div>

        <div className="landing-preview" aria-label="Nexora workspace preview">
          <div className="preview-sidebar">
            <div className="preview-logo">N</div>
            <span /><span /><span /><span /><span />
          </div>
          <div className="preview-main">
            <div className="preview-top"><div><small>Workspace</small><strong>Good morning</strong></div><i /></div>
            <div className="preview-stats"><div /><div /><div /></div>
            <div className="preview-grid">
              <div className="preview-chart"><small>Project progress</small><div className="preview-line"><i /><i /><i /><i /><i /><i /></div></div>
              <div className="preview-list"><small>Today</small><p /><p /><p /></div>
            </div>
          </div>
        </div>
      </section>

      <section className="landing-statement">
        <p className="eyebrow">Built for focused teams</p>
        <h2>Less chasing.<br /><span>More shipping.</span></h2>
        <p>Plan the work, keep everyone aligned, and understand progress without adding another layer of noise.</p>
      </section>

      <section className="landing-pillars" aria-label="Nexora principles">
        <article><span>01</span><h3>Plan</h3><p>Turn goals into clear work your team can actually move forward.</p></article>
        <article><span>02</span><h3>Collaborate</h3><p>Give people ownership and keep the right context close to the work.</p></article>
        <article><span>03</span><h3>Measure</h3><p>See what is moving, what is stuck, and where attention is needed.</p></article>
      </section>

      <section className="landing-final-cta">
        <p className="eyebrow">Ready when you are</p>
        <h2>Make work feel<br /><span>simple again.</span></h2>
        <Link to="/register" className="primary-button">Create your workspace <ArrowRight size={16} /></Link>
      </section>

      <footer className="landing-footer"><span>© {new Date().getFullYear()} Nexora</span><span>Work smarter. Ship faster.</span></footer>
    </main>
  );
}
