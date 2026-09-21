export type AssetStatus = "active" | "inactive" | "decommissioned" | string;

export interface Asset {
  id: string;
  name: string;
  asset_code: string;
  asset_type: string;
  manufacturer: string | null;
  model: string | null;
  serial_number: string | null;
  location: string | null;
  status: AssetStatus;
  commissioned_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface HealthResponse {
  status: string;
}

export interface Sensor {
  id: string;
  asset_id: string;
  name: string;
  sensor_type: string;
  unit: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface SensorReading {
  id: string;
  sensor_id: string;
  recorded_at: string;
  value: number;
  quality: string | null;
  created_at: string;
}

export type AlertStatus = "open" | "acknowledged" | "resolved";

export interface Alert {
  id: string;
  asset_id: string;
  ai_analysis_id: string | null;
  title: string;
  description: string | null;
  severity: "low" | "moderate" | "high" | "critical";
  status: AlertStatus;
  detected_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  engineer_notes: string | null;
  created_at: string;
  updated_at: string;
}

export type MaintenanceStatus = "planned" | "in_progress" | "completed" | "cancelled";

export interface MaintenanceRecord {
  id: string;
  asset_id: string;
  alert_id: string | null;
  maintenance_type: "preventive" | "predictive" | "corrective" | "inspection";
  description: string;
  status: MaintenanceStatus;
  scheduled_for: string | null;
  started_at: string | null;
  completed_at: string | null;
  outcome: string | null;
  engineer_name: string | null;
  created_at: string;
  updated_at: string;
}