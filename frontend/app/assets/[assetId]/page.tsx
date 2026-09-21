import Link from "next/link";

const plannedSections = [
  { number: "01", title: "Overview", description: "Identity, condition, and operating context." },
  { number: "02", title: "Sensors & Telemetry", description: "Live readings and developing equipment trends." },
  { number: "03", title: "AI Analysis", description: "Machine-assisted reliability assessments." },
  { number: "04", title: "Alerts", description: "Signals associated with this asset." },
  { number: "05", title: "Maintenance", description: "Planned and historical reliability work." },
];

export default async function AssetDetailPage({ params }: { params: Promise<{ assetId: string }> }) {
  const { assetId } = await params;

  return (
    <section className="content-section detail-section">
      <Link href="/assets" className="back-link">← Asset register</Link>
      <div className="detail-heading"><div><p className="section-kicker">Asset reference</p><h2>Asset detail</h2><p className="detail-id">{assetId}</p></div><span className="placeholder-status">Progressive view</span></div>
      <div className="detail-grid">{plannedSections.map((section) => <article className="detail-card" key={section.number}><span className="detail-number">{section.number}</span><h3>{section.title}</h3><p>{section.description}</p><span className="detail-card-state">Coming next</span></article>)}</div>
    </section>
  );
}