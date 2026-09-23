import type { UserRole } from "@/lib/auth/types";

export type { UserRole } from "@/lib/auth/types";

export type AssetStatus = "active" | "inactive" | "decommissioned" | string;

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserCreateInput {
  email: string;
  full_name: string;
  password: string;
  role: UserRole;
}

export interface UserUpdateInput {
  full_name?: string;
  role?: UserRole;
  is_active?: boolean;
}

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

export interface AIAnalysis {
  id: string;
  asset_id: string;
  analyzed_at: string;
  risk_score: number | null;
  risk_level: string | null;
  summary: string;
  anomaly_detected: boolean;
  findings: Record<string, unknown> | unknown[] | null;
  recommended_actions: Record<string, unknown> | unknown[] | null;
  model_provider: string | null;
  model_name: string | null;
  created_at: string;
}

export interface AIAnalysisCreateInput {
  limit_per_sensor?: number;
}

export interface AIFinding {
  sensor: string;
  observation: string;
  evidence: string;
  significance: string;
}

export interface AIRecommendedAction {
  action: string;
  rationale: string;
  priority: "low" | "moderate" | "high" | "critical";
}

export interface AIAnalysisFindings {
  model_findings?: AIFinding[];
  limitations?: string[];
  analysis_window?: Record<string, unknown>;
  deterministic_sensor_metrics?: unknown[];
  provider_execution?: Record<string, unknown>;
}

export type ConditionStatus = "insufficient_data" | "normal" | "watch" | "anomalous";

export interface ConditionFinding {
  sensor_id: string;
  sensor_name: string;
  sensor_type: string;
  unit: string;
  latest_value: number | null;
  baseline_value: number | null;
  deviation_score: number | null;
  recent_change: number | null;
  trend_direction: "increasing" | "decreasing" | "stable";
  trend_strength: number | null;
  finding_status: ConditionStatus;
  explanation: string;
}

export interface ConditionAssessment {
  id: string;
  asset_id: string;
  evaluated_at: string;
  evaluated_through: string;
  status: ConditionStatus;
  summary: string;
  findings: ConditionFinding[];
  created_at: string;
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
  condition_assessment_id: string | null;
  condition_assessment_evaluated_at: string | null;
  source: "manual" | "condition_monitoring";
  ai_escalation_status: string | null;
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

export interface AlertCreateInput {
  title: string;
  description?: string;
  severity: Alert["severity"];
}

export interface AlertUpdateInput {
  title?: string;
  description?: string;
  severity?: Alert["severity"];
  engineer_notes?: string;
}

export interface AlertResolveInput {
  engineer_notes?: string;
}

export type MaintenanceType = "preventive" | "predictive" | "corrective" | "inspection";
export type MaintenanceStatus = "planned" | "in_progress" | "completed" | "cancelled";

export interface MaintenanceRecord {
  id: string;
  asset_id: string;
  alert_id: string | null;
  maintenance_type: MaintenanceType;
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

export interface MaintenanceCreateInput {
  maintenance_type: MaintenanceType;
  description: string;
  alert_id?: string | null;
  scheduled_for?: string | null;
  engineer_name?: string | null;
}

export interface MaintenanceUpdateInput {
  maintenance_type?: MaintenanceType;
  description?: string;
  scheduled_for?: string | null;
  engineer_name?: string | null;
  outcome?: string | null;
}

export interface MaintenanceStartInput {
  engineer_name?: string | null;
}

export interface MaintenanceCompleteInput {
  outcome?: string | null;
  engineer_name?: string | null;
}

export interface MaintenanceCancelInput {
  outcome?: string | null;
}
