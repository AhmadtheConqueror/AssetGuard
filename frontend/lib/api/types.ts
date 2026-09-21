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