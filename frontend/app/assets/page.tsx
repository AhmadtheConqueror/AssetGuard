"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getAssets } from "@/lib/api/client";
import type { Asset } from "@/lib/api/types";
import { StatusBadge } from "@/components/StatusBadge";

type LoadState = "loading" | "ready" | "error";

function AssetStatus({ status }: { status: string }) {
  return <StatusBadge value={status} />;
}

export default function AssetsPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");

  useEffect(() => {
    getAssets().then((data) => { setAssets(data); setLoadState("ready"); }).catch(() => setLoadState("error"));
  }, []);

  return (
    <section className="content-section">
      <div className="section-heading">
        <div><p className="section-kicker">Live from the asset register</p><h2>Equipment directory</h2></div>
        {loadState === "ready" && <span className="record-count">{assets.length} {assets.length === 1 ? "asset" : "assets"}</span>}
      </div>
      {loadState === "loading" && <div className="state-panel" aria-live="polite"><span className="loading-pulse" /><div><strong>Loading asset register</strong><p>Connecting to the AssetGuard API.</p></div></div>}
      {loadState === "error" && <div className="state-panel state-panel-error" role="alert"><span className="state-icon">!</span><div><strong>Asset register unavailable</strong><p>We could not load live assets. Check that the backend is running and try again.</p></div></div>}
      {loadState === "ready" && assets.length === 0 && <div className="state-panel"><span className="state-icon">—</span><div><strong>No assets registered</strong><p>The asset register is currently empty.</p></div></div>}
      {loadState === "ready" && assets.length > 0 && <div className="asset-table-wrap"><div className="asset-table" role="table" aria-label="Assets">
        <div className="asset-row asset-row-header" role="row"><span>Asset</span><span>Type</span><span>Location</span><span>Status</span></div>
        {assets.map((asset) => <Link href={`/assets/${asset.id}`} className="asset-row asset-row-data" key={asset.id} role="row"><span className="asset-primary"><strong>{asset.name}</strong><small>{asset.asset_code}</small></span><span>{asset.asset_type}</span><span>{asset.location ?? "Location not set"}</span><span><AssetStatus status={asset.status} /></span></Link>)}
      </div></div>}
    </section>
  );
}
