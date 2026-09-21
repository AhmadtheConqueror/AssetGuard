import type {
  Alert,
  AlertCreateInput,
  AlertResolveInput,
  AlertUpdateInput,
  AIAnalysis,
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

export function getAsset(assetId: string) {
  return getJson<Asset>(`/api/assets/${assetId}`);
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

export function getAIAnalyses(assetId: string) {
  return getJson<AIAnalysis[]>(`/api/assets/${assetId}/ai-analyses`);
}

export function getLatestAIAnalysis(assetId: string) {
  return getJson<AIAnalysis>(`/api/assets/${assetId}/ai-analyses/latest`);
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function requestJson<T>(path: string, method: "POST" | "PATCH", body: unknown): Promise<T> {
  const response = await fetch(getApiUrl(path), {
    method,
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const errorBody = await response.json() as { detail?: string };
      if (errorBody.detail) detail = errorBody.detail;
    } catch {
      // Keep the status-based message when the server does not return JSON.
    }
    throw new ApiError(response.status, detail);
  }

  return response.json() as Promise<T>;
}

export function createAlert(assetId: string, input: AlertCreateInput) {
  return requestJson<Alert>(`/api/assets/${assetId}/alerts`, "POST", input);
}

export function updateAlert(alertId: string, input: AlertUpdateInput) {
  return requestJson<Alert>(`/api/alerts/${alertId}`, "PATCH", input);
}

export function acknowledgeAlert(alertId: string) {
  return requestJson<Alert>(`/api/alerts/${alertId}/acknowledge`, "POST", {});
}

export function resolveAlert(alertId: string, input: AlertResolveInput) {
  return requestJson<Alert>(`/api/alerts/${alertId}/resolve`, "POST", input);
}