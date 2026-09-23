import type {
  Alert,
  AlertCreateInput,
  AlertResolveInput,
  AlertUpdateInput,
  AIAnalysis,
  AIAnalysisCreateInput,
  Asset,
  HealthResponse,
  MaintenanceCancelInput,
  MaintenanceCompleteInput,
  MaintenanceCreateInput,
  MaintenanceRecord,
  MaintenanceStartInput,
  MaintenanceUpdateInput,
  Sensor,
  SensorReading,
  User,
  UserCreateInput,
  UserUpdateInput,
} from "./types";

/**
 * Returns the BFF proxy URL for operational API calls.
 * All requests are routed through /api/backend/... where the
 * Next.js route handler attaches the Authorization header server-side.
 * The JWT never touches browser JavaScript.
 */
function getBffUrl(path: string): string {
  // path always starts with /api/... or /health
  // Strip leading slash for the catch-all segment
  const normalised = path.startsWith("/") ? path.slice(1) : path;
  return `/api/backend/${normalised}`;
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(getBffUrl(path), {
    headers: { Accept: "application/json" },
    cache: "no-store",
    credentials: "same-origin",
  });

  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

/**
 * Health check — calls the public /api/health proxy (no auth required).
 * Kept separate so the sidebar health indicator works even when the
 * session is expired.
 */
export function getHealth() {
  return fetch("/api/health", {
    headers: { Accept: "application/json" },
    cache: "no-store",
  }).then(async (res) => {
    if (!res.ok) throw new Error(`Health check failed with status ${res.status}`);
    return res.json() as Promise<HealthResponse>;
  });
}

export function getAssets() {
  return getJson<Asset[]>("/api/assets");
}

export function getUsers() {
  return getJson<User[]>("/api/users");
}

export function getUser(userId: string) {
  return getJson<User>(`/api/users/${userId}`);
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

function getApiErrorDetail(detail: unknown) {
  if (typeof detail === "string") return detail;
  if (!Array.isArray(detail)) return null;

  const messages = detail
    .map((item) => {
      if (item && typeof item === "object" && "msg" in item) {
        const { msg } = item as { msg?: unknown };
        return typeof msg === "string" ? msg : null;
      }

      return null;
    })
    .filter((message): message is string => Boolean(message));

  return messages.length > 0 ? messages.join(" ") : null;
}

async function requestJson<T>(path: string, method: "POST" | "PATCH", body: unknown): Promise<T> {
  const response = await fetch(getBffUrl(path), {
    method,
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: "same-origin",
  });

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const errorBody = await response.json() as { detail?: unknown };
      detail = getApiErrorDetail(errorBody.detail) ?? detail;
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

export function createUser(input: UserCreateInput) {
  return requestJson<User>("/api/users", "POST", input);
}

export function updateUser(userId: string, input: UserUpdateInput) {
  return requestJson<User>(`/api/users/${userId}`, "PATCH", input);
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

export function createAIAnalysis(assetId: string, input: AIAnalysisCreateInput = {}) {
  const limit = input.limit_per_sensor ?? 50;
  return requestJson<AIAnalysis>(`/api/assets/${assetId}/ai-analyses?limit_per_sensor=${limit}`, "POST", {});
}

export function createMaintenanceRecord(assetId: string, input: MaintenanceCreateInput) {
  return requestJson<MaintenanceRecord>(`/api/assets/${assetId}/maintenance-records`, "POST", input);
}

export function updateMaintenanceRecord(recordId: string, input: MaintenanceUpdateInput) {
  return requestJson<MaintenanceRecord>(`/api/maintenance-records/${recordId}`, "PATCH", input);
}

export function startMaintenance(recordId: string, input: MaintenanceStartInput = {}) {
  return requestJson<MaintenanceRecord>(`/api/maintenance-records/${recordId}/start`, "POST", input);
}

export function completeMaintenance(recordId: string, input: MaintenanceCompleteInput = {}) {
  return requestJson<MaintenanceRecord>(`/api/maintenance-records/${recordId}/complete`, "POST", input);
}

export function cancelMaintenance(recordId: string, input: MaintenanceCancelInput = {}) {
  return requestJson<MaintenanceRecord>(`/api/maintenance-records/${recordId}/cancel`, "POST", input);
}
