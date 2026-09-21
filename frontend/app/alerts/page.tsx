"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertList, CreateAlertForm, alertErrorMessage } from "@/components/AlertWorkflow";
import { getAlerts, getAssets } from "@/lib/api/client";
import type { Alert, Asset } from "@/lib/api/types";

type LoadState = "loading" | "ready" | "error";
type StatusFilter = "all" | Alert["status"];
type SeverityFilter = "all" | Alert["severity"];

export default function AlertsPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<StatusFilter>("all");
  const [severity, setSeverity] = useState<SeverityFilter>("all");
  const [assetId, setAssetId] = useState("all");
  const [titleSearch, setTitleSearch] = useState("");

  useEffect(() => {
    let mounted = true;

    async function loadAlerts() {
      setLoadState("loading");
      try {
        const loadedAssets = await getAssets();
        const results = await Promise.allSettled(loadedAssets.map((asset) => getAlerts(asset.id)));
        const failed = results.some((result) => result.status === "rejected");
        const loadedAlerts = results.flatMap((result) => result.status === "fulfilled" ? result.value : []);
        if (!mounted) return;
        setAssets(loadedAssets);
        setAlerts(loadedAlerts);
        setLoadState(failed ? "error" : "ready");
        setError(failed ? "Some asset alert records could not be loaded." : null);
      } catch (loadError) {
        if (!mounted) return;
        setLoadState("error");
        setError(alertErrorMessage(loadError, "The alert workspace could not be loaded."));
      }
    }

    void loadAlerts();
    return () => { mounted = false; };
  }, []);

  const filteredAlerts = useMemo(() => {
    const query = titleSearch.trim().toLowerCase();
    return alerts.filter((alert) => (
      (status === "all" || alert.status === status)
      && (severity === "all" || alert.severity === severity)
      && (assetId === "all" || alert.asset_id === assetId)
      && (!query || alert.title.toLowerCase().includes(query))
    ));
  }, [alerts, assetId, severity, status, titleSearch]);

  const counts = {
    open: alerts.filter((alert) => alert.status === "open").length,
    acknowledged: alerts.filter((alert) => alert.status === "acknowledged").length,
    resolved: alerts.filter((alert) => alert.status === "resolved").length,
    total: alerts.length,
  };

  function replaceAlert(updatedAlert: Alert) {
    setAlerts((current) => current.map((alert) => alert.id === updatedAlert.id ? updatedAlert : alert));
  }

  function addAlert(alert: Alert) {
    setAlerts((current) => [alert, ...current]);
  }

  return <section className="content-section alerts-workspace">
    <div className="workspace-intro"><div><p className="section-kicker">Signal review</p><h2>Alerts workspace</h2><p className="intro-copy">Review, acknowledge, and resolve equipment signals across the asset register.</p></div><span className="data-badge">LIVE DATA</span></div>
    <div className="alert-count-grid" aria-label="Alert summary"><div><span>Open</span><strong>{counts.open}</strong></div><div><span>Acknowledged</span><strong>{counts.acknowledged}</strong></div><div><span>Resolved</span><strong>{counts.resolved}</strong></div><div><span>Total</span><strong>{counts.total}</strong></div></div>
    {assets.length > 0 && <CreateAlertForm assets={assets} onCreated={addAlert} />}
    <section className="alert-register"><div className="alert-register-heading"><div><p className="section-kicker">Alert register</p><h3>{filteredAlerts.length} matching {filteredAlerts.length === 1 ? "alert" : "alerts"}</h3></div><div className="filter-status">{loadState === "loading" ? "Loading..." : "Live register"}</div></div>
      <div className="alert-filters"><label>Status<select value={status} onChange={(event) => setStatus(event.target.value as StatusFilter)}><option value="all">All statuses</option><option value="open">Open</option><option value="acknowledged">Acknowledged</option><option value="resolved">Resolved</option></select></label><label>Severity<select value={severity} onChange={(event) => setSeverity(event.target.value as SeverityFilter)}><option value="all">All severities</option><option value="low">Low</option><option value="moderate">Moderate</option><option value="high">High</option><option value="critical">Critical</option></select></label><label>Asset<select value={assetId} onChange={(event) => setAssetId(event.target.value)}><option value="all">All assets</option>{assets.map((asset) => <option value={asset.id} key={asset.id}>{asset.name} · {asset.asset_code}</option>)}</select></label><label className="filter-search">Title search<input value={titleSearch} onChange={(event) => setTitleSearch(event.target.value)} placeholder="Search alert titles" /></label></div>
      {error && <div className="alert-workspace-notice" role="alert">{error}</div>}
      {loadState === "loading" && <div className="detail-state"><strong>Loading alert register</strong><p>Fetching assets and their alert records.</p></div>}
      {loadState !== "loading" && filteredAlerts.length === 0 && <div className="detail-state"><strong>{alerts.length === 0 ? "No alerts recorded" : "No matching alerts"}</strong><p>{alerts.length === 0 ? "Create an alert when an equipment signal needs review." : "Adjust the filters to see other records."}</p></div>}
      {filteredAlerts.length > 0 && <AlertList alerts={filteredAlerts} assets={assets} onAlertChange={replaceAlert} />}
    </section>
  </section>;
}