"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ApiError,
  createAIAnalysis,
  getAIAnalyses,
  getAlerts,
  getAsset,
  getLatestSensorReading,
  getMaintenanceRecords,
  getSensorReadings,
  getSensors,
} from "@/lib/api/client";
import { TrendChart } from "@/components/OperationalDashboard";
import { StatusBadge } from "@/components/StatusBadge";
import { AssetDetailSkeleton, RecordSkeletons, SectionSkeleton } from "@/components/Skeleton";
import { formatDateTime, formatSensorValue as formatValue } from "@/lib/format";
import { AlertList } from "@/components/AlertWorkflow";
import { CreateMaintenanceForm, MaintenanceEmptyState, MaintenanceRecordList } from "@/components/MaintenanceWorkflow";
import type {
  AIAnalysis,
  AIAnalysisFindings,
  AIFinding,
  AIRecommendedAction,
  Alert,
  Asset,
  MaintenanceRecord,
  Sensor,
  SensorReading,
} from "@/lib/api/types";

type LoadState = "loading" | "ready" | "error";

interface SensorSnapshot {
  sensor: Sensor;
  latest: SensorReading | null;
  readings: SensorReading[];
}

interface DetailData {
  loading: boolean;
  sensors: SensorSnapshot[];
  analyses: AIAnalysis[];
  alerts: Alert[];
  maintenance: MaintenanceRecord[];
}

const sections = [
  { id: "overview", label: "Overview" },
  { id: "telemetry", label: "Sensors & Telemetry" },
  { id: "ai-analysis", label: "AI Analysis" },
  { id: "alerts", label: "Alerts" },
  { id: "maintenance", label: "Maintenance" },
];

const sensorColors = ["#3d7f73", "#c58b35", "#587c9b", "#9c655a", "#766a9c", "#4e8b8a"];

function SectionState({ title, detail, error = false }: { title: string; detail: string; error?: boolean }) {
  if (title.startsWith("Loading sensor")) return <SectionSkeleton variant="chart" count={2} />;
  if (title.startsWith("Loading")) return <RecordSkeletons count={2} />;
  return <div className={`detail-state ${error ? "detail-state-error" : ""}`} role={error ? "alert" : undefined}><strong>{title}</strong><p>{detail}</p></div>;
}

function isFinding(value: unknown): value is AIFinding {
  return Boolean(value && typeof value === "object" && "sensor" in value && "observation" in value);
}

function isRecommendedAction(value: unknown): value is AIRecommendedAction {
  return Boolean(value && typeof value === "object" && "action" in value && "rationale" in value);
}

function AnalysisCard({ analysis }: { analysis: AIAnalysis }) {
  const findingsPayload = !Array.isArray(analysis.findings) && analysis.findings ? analysis.findings as AIAnalysisFindings : null;
  const findings = (findingsPayload?.model_findings ?? (Array.isArray(analysis.findings) ? analysis.findings : [])).filter(isFinding);
  const actions = (Array.isArray(analysis.recommended_actions) ? analysis.recommended_actions : []).filter(isRecommendedAction);
  const limitations = findingsPayload?.limitations?.filter((item): item is string => typeof item === "string") ?? [];

  return <article className="analysis-card"><div className="analysis-card-header"><div><span>{formatDateTime(analysis.analyzed_at)}</span><h4>{analysis.risk_level ?? "Recorded analysis"}</h4></div>{analysis.risk_score !== null && <strong>{Math.round(analysis.risk_score * 100)}%</strong>}</div><p className="analysis-summary">{analysis.summary}</p><div className="analysis-facts"><span>Anomaly detected <b>{analysis.anomaly_detected ? "Yes" : "No"}</b></span>{analysis.model_provider && <span>Provider <b>{analysis.model_provider}</b></span>}{analysis.model_name && <span>Model <b>{analysis.model_name}</b></span>}</div>{findings.length > 0 && <div className="analysis-detail-group"><h5>Findings</h5><div className="analysis-entry-list">{findings.map((finding, index) => <div key={`${finding.sensor}-${index}`}><div className="analysis-entry-heading"><strong>{finding.sensor}</strong></div><p>{finding.observation}</p>{finding.evidence && <small>Evidence: {finding.evidence}</small>}{finding.significance && <small>Significance: {finding.significance}</small>}</div>)}</div></div>}{actions.length > 0 && <div className="analysis-detail-group"><h5>Recommended actions</h5><div className="analysis-entry-list">{actions.map((action, index) => <div key={`${action.action}-${index}`}><div className="analysis-entry-heading"><strong>{action.action}</strong><StatusBadge value={action.priority} /></div><p>{action.rationale}</p></div>)}</div></div>}{limitations.length > 0 && <div className="analysis-detail-group analysis-limitations"><h5>Limitations</h5><ul>{limitations.map((limitation, index) => <li key={`${limitation}-${index}`}>{limitation}</li>)}</ul></div>}</article>;
}

function AssetHeader({ asset }: { asset: Asset }) {
  const optionalFacts = [
    ["Manufacturer", asset.manufacturer],
    ["Model", asset.model],
    ["Serial number", asset.serial_number],
    ["Commissioned", asset.commissioned_at ? formatDateTime(asset.commissioned_at) : null],
  ].filter(([, value]) => value);

  return <>
    <Link href="/assets" className="back-link">← Asset register</Link>
    <header className="asset-detail-header">
      <div className="asset-detail-title"><p className="section-kicker">Asset reference</p><div className="asset-detail-name"><h2>{asset.name}</h2><span>{asset.asset_code}</span></div><p className="asset-detail-type">{asset.asset_type}</p></div>
      <div className="asset-detail-status"><StatusBadge value={asset.status} /><span>{asset.location ?? "Location not set"}</span></div>
    </header>
    {optionalFacts.length > 0 && <dl className="asset-metadata">{optionalFacts.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>}
  </>;
}

function SectionNav() {
  return <nav className="detail-section-nav" aria-label="Asset detail sections">{sections.map((section) => <a href={`#${section.id}`} key={section.id}>{section.label}</a>)}</nav>;
}

function OverviewSection({ asset, data }: { asset: Asset; data: DetailData }) {
  const latestTimestamp = data.sensors.map(({ latest }) => latest?.recorded_at).filter(Boolean).sort().at(-1) ?? null;
  const openAlerts = data.alerts.filter((alert) => alert.status === "open").length;
  const activeMaintenance = data.maintenance.filter((record) => record.status === "planned" || record.status === "in_progress").length;

  if (data.loading) return <section id="overview" className="detail-section-block" aria-labelledby="overview-title"><div className="detail-section-heading"><div><p className="section-kicker">Operational summary</p><h3 id="overview-title">{asset.name} at a glance</h3></div></div><SectionSkeleton variant="card" count={5} /></section>;

  return <section id="overview" className="detail-section-block" aria-labelledby="overview-title"><div className="detail-section-heading"><div><p className="section-kicker">Operational summary</p><h3 id="overview-title">{asset.name} at a glance</h3></div><StatusBadge value={asset.status} /></div><div className="overview-facts"><div><span>Total sensors</span><strong>{data.sensors.length}</strong></div><div><span>Latest telemetry</span><strong>{latestTimestamp ? formatDateTime(latestTimestamp) : "No readings"}</strong></div><div><span>Open alerts</span><strong>{openAlerts}</strong></div><div><span>Active maintenance</span><strong>{activeMaintenance}</strong></div><div><span>AI history</span><strong>{data.analyses.length > 0 ? `${data.analyses.length} analysis${data.analyses.length === 1 ? "" : "es"}` : "None yet"}</strong></div></div></section>;
}

function TelemetrySection({ state, sensors }: { state: LoadState; sensors: SensorSnapshot[] }) {
  return <section id="telemetry" className="detail-section-block" aria-labelledby="telemetry-title"><div className="detail-section-heading"><div><p className="section-kicker">Live measurements</p><h3 id="telemetry-title">Sensors & Telemetry</h3></div><span className="detail-section-meta">{sensors.length} sensors</span></div>{state === "loading" && <SectionState title="Loading sensor telemetry" detail="Fetching sensors and recent readings." />}{state === "error" && <SectionState title="Telemetry unavailable" detail="This section could not load from the backend." error />}{state === "ready" && sensors.length === 0 && <SectionState title="No sensors registered" detail="No sensors are attached to this asset." />}{state === "ready" && sensors.length > 0 && <div className="detail-telemetry-content"><div className="detail-sensor-grid">{sensors.map(({ sensor, latest }, index) => <article className="detail-sensor-card" style={{ "--sensor-color": sensorColors[index % sensorColors.length] } as React.CSSProperties} key={sensor.id}><div className="detail-sensor-label"><span className="sensor-signal" aria-hidden="true" />{sensor.sensor_type}<StatusBadge value={sensor.status} /></div><h4>{sensor.name}</h4><strong>{formatValue(latest?.value ?? null, sensor.unit)}</strong><p>{latest ? formatDateTime(latest.recorded_at) : "No reading available"}</p>{latest?.quality && <small>Quality: {latest.quality}</small>}</article>)}</div><div className="detail-trend-grid">{sensors.map(({ sensor, readings }) => <TrendChart key={sensor.id} sensorName={sensor.name} unit={sensor.unit} readings={readings} />)}</div></div>}</section>;
}

function AISection({ state, analyses, assetId, onAnalysisCreated }: { state: LoadState; analyses: AIAnalysis[]; assetId: string; onAnalysisCreated: (analysis: AIAnalysis) => void }) {
  const [isRunning, setIsRunning] = useState(false);
  const [runError, setRunError] = useState<{ title: string; detail: string } | null>(null);
  const [runSuccess, setRunSuccess] = useState(false);

  async function runAnalysis() {
    setIsRunning(true);
    setRunError(null);
    setRunSuccess(false);
    try {
      const analysis = await createAIAnalysis(assetId);
      onAnalysisCreated(analysis);
      setRunSuccess(true);
    } catch (error) {
      if (error instanceof ApiError && error.status === 503) {
        setRunError({ title: "AI analysis is temporarily unavailable", detail: "The analysis service could not complete this request. Existing history remains available; try again later." });
      } else if (error instanceof ApiError && error.status === 422) {
        setRunError({ title: "More telemetry is needed", detail: error.message });
      } else {
        setRunError({ title: "AI analysis could not be completed", detail: error instanceof Error ? error.message : "Please try again later." });
      }
    } finally {
      setIsRunning(false);
    }
  }

  return <section id="ai-analysis" className="detail-section-block" aria-labelledby="ai-title"><div className="detail-section-heading"><div><p className="section-kicker">Telemetry assessment</p><h3 id="ai-title">AI Analysis</h3></div><div className="detail-heading-actions"><span className="detail-section-meta">{analyses.length} recorded</span>{state === "ready" && <button type="button" className="primary-small-button" onClick={() => void runAnalysis()} disabled={isRunning}>{isRunning ? "Running Analysis..." : "Run AI Analysis"}</button>}</div></div>{runSuccess && <div className="analysis-run-notice analysis-run-success" role="status"><strong>Analysis complete</strong><span>The latest result has been added to the history below.</span></div>}{runError && <div className="analysis-run-notice analysis-run-error" role="alert"><strong>{runError.title}</strong><span>{runError.detail}</span></div>}{state === "loading" && <SectionState title="Loading analysis history" detail="Checking for previously stored analyses." />}{state === "error" && <SectionState title="Analysis history unavailable" detail="The AI analysis history could not be retrieved." error />}{state === "ready" && analyses.length === 0 && <SectionState title="No AI analysis available yet" detail="Run an analysis to assess the latest stored telemetry for this asset." />}{state === "ready" && analyses.length > 0 && <div className="analysis-list">{analyses.map((analysis) => <AnalysisCard analysis={analysis} key={analysis.id} />)}</div>}</section>;
}

function AlertsSection({ state, alerts, asset, onAlertChange }: { state: LoadState; alerts: Alert[]; asset: Asset; onAlertChange: (alert: Alert) => void }) {
  return <section id="alerts" className="detail-section-block" aria-labelledby="alerts-title"><div className="detail-section-heading"><div><p className="section-kicker">Signal history</p><h3 id="alerts-title">Alerts</h3></div><span className="detail-section-meta">{alerts.length} recorded</span></div>{state === "loading" && <SectionState title="Loading alert history" detail="Fetching alerts for this asset." />}{state === "error" && <SectionState title="Alerts unavailable" detail="The alert history could not be retrieved." error />}{state === "ready" && alerts.length === 0 && <SectionState title="No alerts recorded for this asset." detail="There are no alert records to review." />}{state === "ready" && alerts.length > 0 && <AlertList alerts={alerts} assets={[asset]} showAsset={false} onAlertChange={onAlertChange} />}</section>;
}

function MaintenanceSection({
  state,
  records,
  asset,
  onRecordChange,
  onRecordCreated,
}: {
  state: LoadState;
  records: MaintenanceRecord[];
  asset: Asset;
  onRecordChange: (record: MaintenanceRecord) => void;
  onRecordCreated: (record: MaintenanceRecord) => void;
}) {
  const [isScheduling, setIsScheduling] = useState(false);

  return <section id="maintenance" className="detail-section-block" aria-labelledby="maintenance-title"><div className="detail-section-heading"><div><p className="section-kicker">Reliability history</p><h3 id="maintenance-title">Maintenance</h3></div><div className="detail-heading-actions"><span className="detail-section-meta">{records.length} recorded</span>{state === "ready" && <button type="button" className="primary-small-button" onClick={() => setIsScheduling((current) => !current)}>{isScheduling ? "Close Scheduler" : "Schedule Maintenance"}</button>}</div></div>{state === "loading" && <SectionState title="Loading maintenance history" detail="Fetching maintenance records for this asset." />}{state === "error" && <SectionState title="Maintenance unavailable" detail="The maintenance history could not be retrieved." error />}{state === "ready" && isScheduling && <CreateMaintenanceForm assets={[asset]} defaultAssetId={asset.id} lockAsset onCreated={(record) => { onRecordCreated(record); setIsScheduling(false); }} onCancel={() => setIsScheduling(false)} />}{state === "ready" && records.length === 0 && !isScheduling && <MaintenanceEmptyState hasRecords={false} onSchedule={() => setIsScheduling(true)} />}{state === "ready" && records.length > 0 && <MaintenanceRecordList records={records} assets={[asset]} showAsset={false} onRecordChange={onRecordChange} />}</section>;
}

export function AssetDetailExperience({ assetId }: { assetId: string }) {
  const [asset, setAsset] = useState<Asset | null>(null);
  const [assetState, setAssetState] = useState<LoadState>("loading");
  const [data, setData] = useState<DetailData>({ loading: true, sensors: [], analyses: [], alerts: [], maintenance: [] });
  const [states, setStates] = useState({ sensors: "loading" as LoadState, ai: "loading" as LoadState, alerts: "loading" as LoadState, maintenance: "loading" as LoadState });

  function replaceAlert(updatedAlert: Alert) {
    setData((current) => ({ ...current, alerts: current.alerts.map((alert) => alert.id === updatedAlert.id ? updatedAlert : alert) }));
  }

  function replaceMaintenanceRecord(updatedRecord: MaintenanceRecord) {
    setData((current) => ({ ...current, maintenance: current.maintenance.map((record) => record.id === updatedRecord.id ? updatedRecord : record) }));
  }

  function addMaintenanceRecord(record: MaintenanceRecord) {
    setData((current) => ({ ...current, maintenance: [record, ...current.maintenance] }));
  }

  function addAnalysis(analysis: AIAnalysis) {
    setData((current) => ({ ...current, analyses: [analysis, ...current.analyses.filter((item) => item.id !== analysis.id)] }));
  }

  useEffect(() => {
    let mounted = true;

    async function loadAsset() {
      setAssetState("loading");
      try {
        const loadedAsset = await getAsset(assetId);
        if (!mounted) return;
        setAsset(loadedAsset);
        setAssetState("ready");

        const [sensorsResult, analysesResult, alertsResult, maintenanceResult] = await Promise.allSettled([
          getSensors(assetId),
          getAIAnalyses(assetId),
          getAlerts(assetId),
          getMaintenanceRecords(assetId),
        ]);
        const sensors = sensorsResult.status === "fulfilled" ? sensorsResult.value : [];
        const sensorSnapshots = await Promise.all(sensors.map(async (sensor) => {
          const [latestResult, readingsResult] = await Promise.allSettled([getLatestSensorReading(sensor.id), getSensorReadings(sensor.id)]);
          return { sensor, latest: latestResult.status === "fulfilled" ? latestResult.value : null, readings: readingsResult.status === "fulfilled" ? readingsResult.value : [] };
        }));
        if (!mounted) return;
        setData({ loading: false, sensors: sensorSnapshots, analyses: analysesResult.status === "fulfilled" ? analysesResult.value : [], alerts: alertsResult.status === "fulfilled" ? alertsResult.value : [], maintenance: maintenanceResult.status === "fulfilled" ? maintenanceResult.value : [] });
        setStates({ sensors: sensorsResult.status === "fulfilled" ? "ready" : "error", ai: analysesResult.status === "fulfilled" ? "ready" : "error", alerts: alertsResult.status === "fulfilled" ? "ready" : "error", maintenance: maintenanceResult.status === "fulfilled" ? "ready" : "error" });
      } catch {
        if (mounted) setAssetState("error");
      }
    }

    void loadAsset();
    return () => { mounted = false; };
  }, [assetId]);

  if (assetState === "loading") return <AssetDetailSkeleton />;
  if (assetState === "error" || !asset) return <section className="content-section detail-not-found"><Link href="/assets" className="back-link">← Asset register</Link><SectionState title="Asset not found" detail="This asset could not be loaded. Check the asset ID or return to the asset register." error /></section>;

  return <section className="content-section asset-detail-page"><AssetHeader asset={asset} /><SectionNav /><OverviewSection asset={asset} data={data} /><TelemetrySection state={states.sensors} sensors={data.sensors} /><AISection state={states.ai} analyses={data.analyses} assetId={asset.id} onAnalysisCreated={addAnalysis} /><AlertsSection state={states.alerts} alerts={data.alerts} asset={asset} onAlertChange={replaceAlert} /><MaintenanceSection state={states.maintenance} records={data.maintenance} asset={asset} onRecordChange={replaceMaintenanceRecord} onRecordCreated={addMaintenanceRecord} /></section>;
}
