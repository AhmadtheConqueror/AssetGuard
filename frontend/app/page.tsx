import Link from "next/link";

export default function Home() {
  return (
    <section className="content-section dashboard-section">
      <div className="dashboard-intro"><div><p className="section-kicker">AI-assisted predictive maintenance</p><h2>Keep critical equipment in view.</h2><p className="intro-copy">AssetGuard brings asset context, telemetry, alerts, and maintenance planning into one working surface.</p></div><div className="intro-accent" aria-hidden="true"><span>AG</span></div></div>
      <div className="dashboard-grid"><Link href="/assets" className="dashboard-card dashboard-card-primary"><span className="card-label">Start with the register</span><h3>View assets</h3><p>Open the live equipment directory and inspect an asset workspace.</p><span className="card-arrow" aria-hidden="true">↗</span></Link><div className="dashboard-card dashboard-card-muted"><span className="card-label">Foundation</span><h3>Live API connection</h3><p>The system status indicator in the shell reflects the FastAPI health endpoint.</p><span className="card-rule" aria-hidden="true" /></div></div>
      <div className="dashboard-footer-note"><span className="footer-line" aria-hidden="true" /><p>Built for engineers who keep infrastructure dependable.</p></div>
    </section>
  );
}
