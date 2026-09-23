import type { SessionUser, UserRole } from "./types";

export type Permission =
  | "readOperational"
  | "manageAssets"
  | "manageSensors"
  | "createSensorReading"
  | "runAIAnalysis"
  | "createAlert"
  | "editAlert"
  | "acknowledgeAlert"
  | "resolveAlert"
  | "createMaintenance"
  | "editMaintenance"
  | "startMaintenance"
  | "completeMaintenance"
  | "cancelMaintenance"
  | "administerUsers";

export const USER_ROLES: readonly UserRole[] = ["admin", "engineer", "technician", "viewer"];

export const DEFAULT_NEW_USER_ROLE: UserRole = "viewer";

export const ROLE_LABELS: Record<UserRole, string> = {
  admin: "Admin",
  engineer: "Engineer",
  technician: "Technician",
  viewer: "Viewer",
};

export const PERMISSION_DENIED_MESSAGE = "You do not have permission to perform this action.";

const rolePermissions: Record<UserRole, ReadonlySet<Permission>> = {
  admin: new Set([
    "readOperational",
    "manageAssets",
    "manageSensors",
    "createSensorReading",
    "runAIAnalysis",
    "createAlert",
    "editAlert",
    "acknowledgeAlert",
    "resolveAlert",
    "createMaintenance",
    "editMaintenance",
    "startMaintenance",
    "completeMaintenance",
    "cancelMaintenance",
    "administerUsers",
  ]),
  engineer: new Set([
    "readOperational",
    "runAIAnalysis",
    "createAlert",
    "editAlert",
    "acknowledgeAlert",
    "resolveAlert",
    "createMaintenance",
    "editMaintenance",
    "startMaintenance",
    "completeMaintenance",
    "cancelMaintenance",
  ]),
  technician: new Set([
    "readOperational",
    "acknowledgeAlert",
    "startMaintenance",
    "completeMaintenance",
  ]),
  viewer: new Set(["readOperational"]),
};

function getRole(subject: SessionUser | UserRole | null | undefined): UserRole | null {
  if (!subject) return null;
  return typeof subject === "string" ? subject : subject.role;
}

export function hasPermission(
  subject: SessionUser | UserRole | null | undefined,
  permission: Permission,
): boolean {
  const role = getRole(subject);
  return role ? rolePermissions[role].has(permission) : false;
}
