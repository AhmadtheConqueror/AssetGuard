"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  getAlerts,
  getAssets,
  getLatestSensorReading,
  getMaintenanceRecords,
  getSensorReadings,
  getSensors,
} from "@/lib/api/client";
import type {
  Alert,
  Asset,
  MaintenanceRecord,
  Sensor,
  SensorReading,
} from "@/lib/api/types";
import { StatusBadge } from "@/components/StatusBadge";
import { DashboardSkeleton } from "@/components/Skeleton";
import { formatDateTime, formatLabel, formatSensorValue } from "@/lib/format";

type SectionState = "loading" | "ready" | "error";

interface SensorSnapshot {
  sensor: Sensor;
  latest: SensorReading | null;
  readings: SensorReading[];
}

interface AssetSnapshot {
  asset: Asset;
  sensors: SensorSnapshot[];
  alerts: Alert[];
  maintenance: MaintenanceRecord[];
  sensorsState: SectionState;
  alertsState: SectionState;
  maintenanceState: SectionState;
}

interface TrendChartProps {
  sensorName: string;
  unit: string;
  readings: SensorReading[];
}

const chartColors = ["#628b82", "#b59762", "#748e9f", "#987a73", "#817b96", "#668f8d"];

export function formatChange(readings: SensorReading[]) {
  if (readings.length < 2) return "Trend needs more readings";

  const first = readings[0].value;
  const last = readings[readings.length - 1].value;
  const difference = last - first;
  const sign = difference > 0 ? "+" : "";

  return `${sign}${new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(difference)} over ${readings.length} readings`;
}

export function TrendChart({ sensorName, unit, readings }: TrendChartProps) {
  const sortedReadings = [...readings].sort(
    (first, second) => new Date(first.recorded_at).getTime() - new Date(second.recorded_at).getTime(),
  );
  const chartWidth = 620;
  const chartHeight = 190;
  const chartPadding = { top: 20, right: 22, bottom: 34, left: 48 };
  const plotWidth = chartWidth - chartPadding.left - chartPadding.right;
  const plotHeight = chartHeight - chartPadding.top - chartPadding.bottom;
  const values = sortedReadings.map((reading) => reading.value);
  const minimum = values.length ? Math.min(...values) : 0;
  const maximum = values.length ? Math.max(...values) : 1;
  const range = maximum - minimum || Math.max(Math.abs(maximum) * 0.08, 1);
  const lowerBound = minimum - range * 0.12;
  const upperBound = maximum + range * 0.12;
  const valueToY = (value: number) => chartPadding.top + ((upperBound - value) / (upperBound - lowerBound)) * plotHeight;
  const points = sortedReadings.map((reading, index) => {
    const x = chartPadding.left + (sortedReadings.length === 1 ? plotWidth / 2 : (index / (sortedReadings.length - 1)) * plotWidth);
    return { x, y: valueToY(reading.value), reading };
  });
  const pointString = points.map((point) => `${point.x},${point.y}`).join(" ");
  const midValue = (minimum + maximum) / 2;

  return (
    <div className="trend-chart-wrap">
      <div className="trend-chart-header">
        <div>
          <h4>{sensorName}</h4>
          <span>{unit} · recent readings</span>
        </div>
        <span className="trend-change">{formatChange(sortedReadings)}</span>
      </div>
      {sortedReadings.length < 2 ? (
        <div className="chart-empty">Not enough historical readings for a trend.</div>
      ) : (
        <svg className="trend-chart" viewBox={`0 0 ${chartWidth} ${chartHeight}`} role="img" aria-label={`${sensorName} trend in ${unit}`}>
          <line x1={chartPadding.left} y1={chartPadding.top} x2={chartPadding.left} y2={chartHeight - chartPadding.bottom} className="chart-axis" />
          <line x1={chartPadding.left} y1={chartHeight - chartPadding.bottom} x2={chartWidth - chartPadding.right} y2={chartHeight - chartPadding.bottom} className="chart-axis" />
          <line x1={chartPadding.left} y1={chartPadding.top + plotHeight / 2} x2={chartWidth - chartPadding.right} y2={chartPadding.top + plotHeight / 2} className="chart-gridline" />
          <text x="5" y={chartPadding.top + 4} className="chart-label">{maximum.toFixed(1)}</text>
          <text x="5" y={chartPadding.top + plotHeight / 2 + 4} className="chart-label">{midValue.toFixed(1)}</text>
          <text x="5" y={chartHeight - chartPadding.bottom + 4} className="chart-label">{minimum.toFixed(1)}</text>
          <polyline points={pointString} className="chart-line" />
          {points.map((point) => (
            <circle key={point.reading.id} cx={point.x} cy={point.y} r="3.5" className="chart-point">
              <title>{`${formatSensorValue(point.reading.value, unit)} · ${formatDateTime(point.reading.recorded_at)}`}</title>
            </circle>
          ))}
          <text x={chartPadding.left} y={chartHeight - 8} className="chart-label">{formatDateTime(sortedReadings[0].recorded_at)}</text>
          <text x={chartWidth - chartPadding.right} y={chartHeight - 8} textAnchor="end" className="chart-label">{formatDateTime(sortedReadings.at(-1)?.recorded_at ?? null)}</text>
        </svg>
      )}
    </div>
  );
}

function SectionMessage({ title, detail, error = false }: { title: string; detail: string; error?: boolean }) {
  return <div className={`dashboard-section-message ${error ? "dashboard-section-message-error" : ""}`}><strong>{title}</strong><p>{detail}</p></div>;
}

function SensorCard({ snapshot, colorIndex }: { snapshot: SensorSnapshot; colorIndex: number }) {
  const { sensor, latest } = snapshot;
  const color = chartColors[colorIndex % chartColors.length];

  return (
    <article className="sensor-card" style={{ "--sensor-color": color } as React.CSSProperties}>
      <div className="sensor-card-topline"><span className="sensor-signal" aria-hidden="true" /><span>{sensor.sensor_type}</span><span className="sensor-status">{sensor.status}</span></div>
      <h3>{sensor.name}</h3>
      <div className="sensor-value">{formatSensorValue(latest?.value ?? null, sensor.unit)}</div>
      <p className="sensor-timestamp">{latest ? `Updated ${formatDateTime(latest.recorded_at)}` : "No reading available"}</p>
      {latest?.quality && <span className="quality-label">Quality: {latest.quality}</span>}
    </article>
  );
}

function AssetTelemetry({ snapshot, lastUpdated }: { snapshot: AssetSnapshot; lastUpdated: Date | null }) {
  return (
    <section className="dashboard-block telemetry-block">
      <div className="dashboard-block-heading"><div><p className="section-kicker">Live telemetry</p><h2>Sensor readings</h2></div><div className="live-update-meta"><span className="live-indicator">LIVE</span><span className="block-meta">{snapshot.sensors.length} sensors{lastUpdated ? ` · Last updated: ${lastUpdated.toLocaleTimeString()}` : ""}</span></div></div>
      {snapshot.sensorsState === "loading" && <SectionMessage title="Loading telemetry" detail="Fetching sensors and recent readings from the API." />}
      {snapshot.sensorsState === "error" && <SectionMessage title="Telemetry unavailable" detail="The asset loaded, but its sensor data could not be retrieved." error />}
      {snapshot.sensorsState === "ready" && snapshot.sensors.length === 0 && <SectionMessage title="No sensors registered" detail="This asset does not have sensors connected yet." />}
      {snapshot.sensorsState === "ready" && snapshot.sensors.length > 0 && <>
        <div className="sensor-grid">{snapshot.sensors.map((sensor, index) => <SensorCard key={sensor.sensor.id} snapshot={sensor} colorIndex={index} />)}</div>
        <div className="trend-grid">{snapshot.sensors.map((sensor) => <TrendChart key={sensor.sensor.id} sensorName={sensor.sensor.name} unit={sensor.sensor.unit} readings={sensor.readings} />)}</div>
      </>}
    </section>
  );
}

function AlertsSummary({ snapshot }: { snapshot: AssetSnapshot }) {
  const openAlerts = snapshot.alerts.filter((alert) => alert.status === "open");

  return <section className="summary-panel"><div className="summary-panel-heading"><div><p className="section-kicker">Signal review</p><h2>Alerts</h2></div><span className="summary-count">{openAlerts.length}</span></div>{snapshot.alertsState === "loading" && <SectionMessage title="Loading alerts" detail="Checking the current alert register." />}{snapshot.alertsState === "error" && <SectionMessage title="Alerts unavailable" detail="The alert register could not be reached." error />}{snapshot.alertsState === "ready" && openAlerts.length === 0 && <SectionMessage title="No open alerts" detail="There are no open alerts for this asset." />}{snapshot.alertsState === "ready" && openAlerts.length > 0 && <div className="summary-list">{openAlerts.map((alert) => <div className="summary-list-item" key={alert.id}><span className={`severity-mark severity-${alert.severity}`} aria-hidden="true" /><div><strong>{alert.title}</strong><p>{alert.severity} · detected {formatDateTime(alert.detected_at)}</p></div></div>)}</div>}</section>;
}

function MaintenanceSummary({ snapshot }: { snapshot: AssetSnapshot }) {
  const activeMaintenance = snapshot.maintenance.filter((record) => record.status === "planned" || record.status === "in_progress");

  return <section className="summary-panel"><div className="summary-panel-heading"><div><p className="section-kicker">Reliability work</p><h2>Maintenance</h2></div><span className="summary-count">{activeMaintenance.length}</span></div>{snapshot.maintenanceState === "loading" && <SectionMessage title="Loading maintenance" detail="Checking planned and active work." />}{snapshot.maintenanceState === "error" && <SectionMessage title="Maintenance unavailable" detail="Maintenance records could not be reached." error />}{snapshot.maintenanceState === "ready" && activeMaintenance.length === 0 && <SectionMessage title="No active maintenance" detail="There is no planned or in-progress work for this asset." />}{snapshot.maintenanceState === "ready" && activeMaintenance.length > 0 && <div className="summary-list">{activeMaintenance.map((record) => <div className="summary-list-item" key={record.id}><span className="maintenance-mark" aria-hidden="true">{record.status === "planned" ? "P" : "I"}</span><div><strong>{record.description}</strong><p>{formatLabel(record.maintenance_type)} · {formatLabel(record.status)}</p></div></div>)}</div>}</section>;
}

export function OperationalDashboard() {
  const [assetSnapshots, setAssetSnapshots] = useState<AssetSnapshot[]>([]);
  const [assetsState, setAssetsState] = useState<SectionState>("loading");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    let mounted = true;
    let refreshing = false;
    let lastSnapshots: AssetSnapshot[] = [];

    async function loadDashboard(initial = false) {
      if (refreshing) return;
      refreshing = true;
      if (initial) setAssetsState("loading");
      try {
        const assets = await getAssets();
        const snapshots = await Promise.all(assets.map(async (asset): Promise<AssetSnapshot> => {
          const previousAsset = lastSnapshots.find((snapshot) => snapshot.asset.id === asset.id);
          const [sensorsResult, alertsResult, maintenanceResult] = await Promise.allSettled([
            getSensors(asset.id),
            getAlerts(asset.id),
            getMaintenanceRecords(asset.id),
          ]);
          const sensors = sensorsResult.status === "fulfilled" ? sensorsResult.value : previousAsset?.sensors.map(({ sensor }) => sensor) ?? [];
          const sensorSnapshots = await Promise.all(sensors.map(async (sensor) => {
            const previousSensor = previousAsset?.sensors.find((snapshot) => snapshot.sensor.id === sensor.id);
            const [latestResult, readingsResult] = await Promise.allSettled([getLatestSensorReading(sensor.id), getSensorReadings(sensor.id)]);
            return {
              sensor,
              latest: latestResult.status === "fulfilled" ? latestResult.value : previousSensor?.latest ?? null,
              readings: readingsResult.status === "fulfilled" ? readingsResult.value : previousSensor?.readings ?? [],
            };
          }));

          return {
            asset,
            sensors: sensorSnapshots,
            alerts: alertsResult.status === "fulfilled" ? alertsResult.value : previousAsset?.alerts ?? [],
            maintenance: maintenanceResult.status === "fulfilled" ? maintenanceResult.value : previousAsset?.maintenance ?? [],
            sensorsState: sensorsResult.status === "fulfilled" ? "ready" : previousAsset?.sensorsState ?? "error",
            alertsState: alertsResult.status === "fulfilled" ? "ready" : previousAsset?.alertsState ?? "error",
            maintenanceState: maintenanceResult.status === "fulfilled" ? "ready" : previousAsset?.maintenanceState ?? "error",
          };
        }));

        if (mounted) {
          lastSnapshots = snapshots;
          setAssetSnapshots(snapshots);
          setAssetsState("ready");
          setLastUpdated(new Date());
        }
      } catch {
        if (mounted && initial) setAssetsState("error");
      } finally {
        refreshing = false;
      }
    }

    void loadDashboard(true);
    const interval = window.setInterval(() => void loadDashboard(), 5000);
    return () => { mounted = false; window.clearInterval(interval); };
  }, []);

  const totalAssets = assetSnapshots.length;
  const activeAssets = assetSnapshots.filter(({ asset }) => asset.status === "active").length;
  const openAlerts = assetSnapshots.reduce((total, snapshot) => total + snapshot.alerts.filter((alert) => alert.status === "open").length, 0);
  const activeMaintenance = assetSnapshots.reduce((total, snapshot) => total + snapshot.maintenance.filter((record) => record.status === "planned" || record.status === "in_progress").length, 0);

  return (
    <section className="content-section dashboard-section operational-dashboard">
      <div className="dashboard-intro dashboard-intro-compact"><div><p className="section-kicker">Operational view</p><p className="intro-copy">Live asset, telemetry, signal, and reliability status from the AssetGuard API.</p></div><span className="data-badge">LIVE DATA</span></div>

      {assetsState !== "loading" && <div className="kpi-grid" aria-label="Operational summary">
        <div className="kpi-card"><span>Total assets</span><strong>{totalAssets}</strong><small>Registered equipment</small></div>
        <div className="kpi-card"><span>Active assets</span><strong>{activeAssets}</strong><small>Currently active</small></div>
        <div className="kpi-card"><span>Open alerts</span><strong>{openAlerts}</strong><small>Awaiting review</small></div>
        <div className="kpi-card"><span>Maintenance</span><strong>{activeMaintenance}</strong><small>Planned or in progress</small></div>
      </div>}

      {assetsState === "loading" && <DashboardSkeleton />}
      {assetsState === "error" && <SectionMessage title="Dashboard data unavailable" detail="The asset register could not be reached. The shell remains available while the backend is offline." error />}
      {assetsState === "ready" && assetSnapshots.length === 0 && <SectionMessage title="No assets registered" detail="Add an asset through the backend before using the operational dashboard." />}
      {assetsState === "ready" && assetSnapshots.map((snapshot) => <div key={snapshot.asset.id} className="asset-dashboard-group">
        <section className="asset-overview-row"><div><p className="section-kicker">Monitored asset</p><Link href={`/assets/${snapshot.asset.id}`} className="asset-overview-link"><h2>{snapshot.asset.name}</h2><span>{snapshot.asset.asset_code}</span></Link></div><div className="asset-overview-facts"><span><b>Type</b>{snapshot.asset.asset_type}</span><span><b>Location</b>{snapshot.asset.location ?? "Not set"}</span><span><b>Status</b><StatusBadge value={snapshot.asset.status} /></span></div></section>
        <AssetTelemetry snapshot={snapshot} lastUpdated={lastUpdated} />
        <div className="summary-grid"><AlertsSummary snapshot={snapshot} /><MaintenanceSummary snapshot={snapshot} /></div>
      </div>)}
    </section>
  );
}
