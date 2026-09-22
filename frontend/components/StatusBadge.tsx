import { formatLabel } from "@/lib/format";

function statusClass(value: string) {
  return value.toLowerCase().replace(/_/g, "-").replace(/\s+/g, "-");
}

export function StatusBadge({ value, kind = "status" }: { value: string; kind?: "status" | "severity" | "maintenance" }) {
  return <span className={`detail-badge detail-badge-${kind} detail-badge-${statusClass(value)}`}>{formatLabel(value)}</span>;
}
