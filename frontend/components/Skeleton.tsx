type SkeletonVariant = "text" | "card" | "metric" | "row" | "chart";

export function Skeleton({ variant = "text", className = "" }: { variant?: SkeletonVariant; className?: string }) {
  return <span className={`skeleton skeleton-${variant} ${className}`.trim()} aria-hidden="true" />;
}

export function RecordSkeletons({ count = 3 }: { count?: number }) {
  return <div className="skeleton-record-list" aria-hidden="true">{Array.from({ length: count }, (_, index) => <div className="skeleton-record" key={index}><Skeleton className="skeleton-title" /><div className="skeleton-badge-row"><Skeleton className="skeleton-badge" /><Skeleton className="skeleton-badge" /></div><Skeleton className="skeleton-copy" /><Skeleton className="skeleton-copy-short" /></div>)}</div>;
}

export function SectionSkeleton({ variant = "card", count = 2 }: { variant?: "card" | "chart" | "row"; count?: number }) {
  return <div className={`skeleton-section skeleton-section-${variant}`} aria-hidden="true">{Array.from({ length: count }, (_, index) => <Skeleton variant={variant} key={index} />)}</div>;
}

export function DashboardSkeleton() {
  return <div className="dashboard-skeleton" aria-label="Loading operational dashboard" role="status"><span className="sr-only">Loading operational dashboard</span><div className="kpi-grid">{Array.from({ length: 4 }, (_, index) => <Skeleton variant="metric" key={index} />)}</div><div className="skeleton-asset-overview"><Skeleton className="skeleton-title" /><Skeleton className="skeleton-copy-short" /></div><div className="skeleton-panel"><div className="sensor-grid">{Array.from({ length: 4 }, (_, index) => <Skeleton variant="card" key={index} />)}</div><div className="trend-grid">{Array.from({ length: 2 }, (_, index) => <Skeleton variant="chart" key={index} />)}</div></div><div className="summary-grid">{Array.from({ length: 2 }, (_, index) => <Skeleton variant="card" key={index} />)}</div></div>;
}

export function AssetDetailSkeleton() {
  return <section className="content-section asset-detail-page detail-skeleton" aria-label="Loading asset detail" role="status"><span className="sr-only">Loading asset detail</span><div className="skeleton-detail-header"><div><Skeleton className="skeleton-kicker" /><Skeleton className="skeleton-heading" /><Skeleton className="skeleton-copy-short" /></div><Skeleton className="skeleton-badge" /></div><div className="skeleton-metadata">{Array.from({ length: 4 }, (_, index) => <Skeleton variant="text" key={index} />)}</div>{Array.from({ length: 3 }, (_, index) => <div className="detail-section-block" key={index}><div className="skeleton-section-heading"><Skeleton className="skeleton-title" /><Skeleton className="skeleton-badge" /></div><SectionSkeleton variant={index === 1 ? "chart" : "card"} count={index === 1 ? 2 : 3} /></div>)}</section>;
}
