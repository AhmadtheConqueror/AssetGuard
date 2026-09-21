import Link from "next/link";

export function PagePlaceholder({ label, title, description }: { label: string; title: string; description: string }) {
  return (
    <section className="placeholder-view">
      <div className="placeholder-kicker">{label}</div>
      <h2>{title}</h2>
      <p>{description}</p>
      <div className="placeholder-line" aria-hidden="true" />
      <span className="placeholder-status">View foundation ready</span>
      <Link href="/" className="text-link">Return to overview</Link>
    </section>
  );
}