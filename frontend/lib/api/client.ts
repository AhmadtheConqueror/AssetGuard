import type {
  Alert,
  Asset,
  HealthResponse,
  MaintenanceRecord,
  Sensor,
  SensorReading,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

function getApiUrl(path: string) {
  if (!API_BASE_URL) {
    throw new Error("NEXT_PUBLIC_API_URL is not configured");
  }

  return `${API_BASE_URL.replace(/\/$/, "")}${path}`;
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(getApiUrl(path), {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function getHealth() {
  return getJson<HealthResponse>("/health");
}

export function getAssets() {
  return getJson<Asset[]>("/api/assets");
}

export function getSensors(assetId: string) {
  return getJson<Sensor[]>(`/api/assets/${assetId}/sensors`);
}

export function getLatestSensorReading(sensorId: string) {
  return getJson<SensorReading>(`/api/sensors/${sensorId}/readings/latest`);
}

export function getSensorReadings(sensorId: string) {
  return getJson<SensorReading[]>(`/api/sensors/${sensorId}/readings?limit=100`);
}

export function getAlerts(assetId: string) {
  return getJson<Alert[]>(`/api/assets/${assetId}/alerts`);
}

export function getMaintenanceRecords(assetId: string) {
  return getJson<MaintenanceRecord[]>(`/api/assets/${assetId}/maintenance-records`);
}