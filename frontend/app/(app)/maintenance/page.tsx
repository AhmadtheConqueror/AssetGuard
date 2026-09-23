"use client";

import { useEffect, useMemo, useState } from "react";
import {
  CreateMaintenanceForm,
  MaintenanceEmptyState,
  MaintenanceRecordList,
  maintenanceErrorMessage,
  maintenanceTypes,
} from "@/components/MaintenanceWorkflow";
import { RecordSkeletons } from "@/components/Skeleton";
import { getAssets, getMaintenanceRecords } from "@/lib/api/client";
import { useSession } from "@/lib/auth/SessionContext";
import { hasPermission } from "@/lib/auth/permissions";
import type { Asset, MaintenanceRecord, MaintenanceStatus, MaintenanceType } from "@/lib/api/types";

type LoadState = "loading" | "ready" | "error";
type StatusFilter = "all" | MaintenanceStatus;
type TypeFilter = "all" | MaintenanceType;

export default function MaintenancePage() {
  const { user } = useSession();
  const [assets, setAssets] = useState<Asset[]>([]);
  const [records, setRecords] = useState<MaintenanceRecord[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<StatusFilter>("all");
  const [maintenanceType, setMaintenanceType] = useState<TypeFilter>("all");
  const [assetId, setAssetId] = useState("all");
  const [search, setSearch] = useState("");
  const [isScheduling, setIsScheduling] = useState(false);
  const canCreateMaintenance = hasPermission(user, "createMaintenance");

  useEffect(() => {
    let mounted = true;

    async function loadMaintenance() {
      setLoadState("loading");
      try {
        const loadedAssets = await getAssets();
        const results = await Promise.allSettled(loadedAssets.map((asset) => getMaintenanceRecords(asset.id)));
        const failed = results.some((result) => result.status === "rejected");
        const loadedRecords = results.flatMap((result) => result.status === "fulfilled" ? result.value : []);
        if (!mounted) return;
        setAssets(loadedAssets);
        setRecords(loadedRecords);
        setLoadState(failed ? "error" : "ready");
        setError(failed ? "Some asset maintenance records could not be loaded." : null);
      } catch (loadError) {
        if (!mounted) return;
        setLoadState("error");
        setError(maintenanceErrorMessage(loadError, "The maintenance workspace could not be loaded."));
      }
    }

    void loadMaintenance();
    return () => { mounted = false; };
  }, []);

  const filteredRecords = useMemo(() => {
    const query = search.trim().toLowerCase();
    return records.filter((record) => (
      (status === "all" || record.status === status)
      && (maintenanceType === "all" || record.maintenance_type === maintenanceType)
      && (assetId === "all" || record.asset_id === assetId)
      && (!query || record.description.toLowerCase().includes(query) || (record.engineer_name ?? "").toLowerCase().includes(query))
    ));
  }, [assetId, maintenanceType, records, search, status]);

  const counts = {
    planned: records.filter((record) => record.status === "planned").length,
    inProgress: records.filter((record) => record.status === "in_progress").length,
    completed: records.filter((record) => record.status === "completed").length,
    cancelled: records.filter((record) => record.status === "cancelled").length,
    total: records.length,
  };

  function addRecord(record: MaintenanceRecord) {
    setRecords((current) => [record, ...current]);
    setIsScheduling(false);
  }

  function replaceRecord(updatedRecord: MaintenanceRecord) {
    setRecords((current) => current.map((record) => record.id === updatedRecord.id ? updatedRecord : record));
  }

  return <section className="content-section maintenance-workspace">
    <div className="workspace-intro"><div><p className="section-kicker">Reliability work</p><h2>Maintenance workspace</h2><p className="intro-copy">Schedule, filter, start, complete, and cancel maintenance work across monitored assets.</p></div><div className="workspace-actions"><span className="data-badge">LIVE DATA</span>{canCreateMaintenance && <button type="button" className="primary-small-button" disabled={assets.length === 0} onClick={() => setIsScheduling((current) => !current)}>{isScheduling ? "Close Scheduler" : "Schedule Maintenance"}</button>}</div></div>
    <div className="maintenance-count-grid" aria-label="Maintenance summary"><div><span>Planned</span><strong>{counts.planned}</strong></div><div><span>In Progress</span><strong>{counts.inProgress}</strong></div><div><span>Completed</span><strong>{counts.completed}</strong></div><div><span>Cancelled</span><strong>{counts.cancelled}</strong></div><div><span>Total</span><strong>{counts.total}</strong></div></div>
    {isScheduling && assets.length > 0 && canCreateMaintenance && <CreateMaintenanceForm assets={assets} onCreated={addRecord} onCancel={() => setIsScheduling(false)} />}
    <section className="maintenance-register"><div className="alert-register-heading"><div><p className="section-kicker">Maintenance register</p><h3>{filteredRecords.length} matching {filteredRecords.length === 1 ? "record" : "records"}</h3></div><div className="filter-status">{loadState === "loading" ? "Updating register" : "Live register"}</div></div>
      <div className="maintenance-filters"><label>Status<select value={status} onChange={(event) => setStatus(event.target.value as StatusFilter)}><option value="all">All statuses</option><option value="planned">Planned</option><option value="in_progress">In progress</option><option value="completed">Completed</option><option value="cancelled">Cancelled</option></select></label><label>Type<select value={maintenanceType} onChange={(event) => setMaintenanceType(event.target.value as TypeFilter)}><option value="all">All types</option>{maintenanceTypes.map((type) => <option value={type} key={type}>{type.replace("_", " ")}</option>)}</select></label><label>Asset<select value={assetId} onChange={(event) => setAssetId(event.target.value)}><option value="all">All assets</option>{assets.map((asset) => <option value={asset.id} key={asset.id}>{asset.name} - {asset.asset_code}</option>)}</select></label><label className="filter-search">Search<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Description or engineer" /></label></div>
      {error && <div className="alert-workspace-notice" role="alert">{error}</div>}
      {loadState === "loading" && <RecordSkeletons />}
      {loadState !== "loading" && filteredRecords.length === 0 && <MaintenanceEmptyState hasRecords={records.length > 0} canSchedule={canCreateMaintenance && assets.length > 0} onSchedule={canCreateMaintenance ? () => setIsScheduling(true) : undefined} />}
      {filteredRecords.length > 0 && <MaintenanceRecordList records={filteredRecords} assets={assets} onRecordChange={replaceRecord} />}
    </section>
  </section>;
}
