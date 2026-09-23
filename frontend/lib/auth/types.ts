export type UserRole = "admin" | "engineer" | "technician" | "viewer";

export interface SessionUser {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Session {
  user: SessionUser;
}
