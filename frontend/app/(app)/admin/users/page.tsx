"use client";

import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ApiError, createUser, getUsers, updateUser } from "@/lib/api/client";
import { StatusBadge } from "@/components/StatusBadge";
import { RecordSkeletons } from "@/components/Skeleton";
import { formatDateTime } from "@/lib/format";
import { useSession } from "@/lib/auth/SessionContext";
import {
  DEFAULT_NEW_USER_ROLE,
  hasPermission,
  PERMISSION_DENIED_MESSAGE,
  ROLE_LABELS,
  USER_ROLES,
} from "@/lib/auth/permissions";
import type { User, UserCreateInput, UserRole, UserUpdateInput } from "@/lib/api/types";

type LoadState = "loading" | "ready" | "error";
type SaveState = "idle" | "saving";

const initialCreateForm: UserCreateInput = {
  email: "",
  full_name: "",
  password: "",
  role: DEFAULT_NEW_USER_ROLE,
};

function userErrorMessage(error: unknown, fallback: string) {
  if (error instanceof ApiError) {
    if (error.status === 403) return PERMISSION_DENIED_MESSAGE;
    if (error.status === 404) return "This user no longer exists.";
    if (error.status === 409) return error.message || "This user change conflicts with another account.";
    if (error.status === 422) return error.message || "Check the user details and try again.";
    return error.message || fallback;
  }

  if (error instanceof Error) return error.message || fallback;
  return fallback;
}

function RoleSelect({
  value,
  onChange,
}: {
  value: UserRole;
  onChange: (role: UserRole) => void;
}) {
  return (
    <select value={value} onChange={(event) => onChange(event.target.value as UserRole)}>
      {USER_ROLES.map((role) => <option value={role} key={role}>{ROLE_LABELS[role]}</option>)}
    </select>
  );
}

function CreateUserPanel({
  onCreated,
  onCancel,
}: {
  onCreated: () => Promise<void>;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<UserCreateInput>(initialCreateForm);
  const [state, setState] = useState<SaveState>("idle");
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!form.email.trim() || !form.full_name.trim() || !form.password) return;

    setState("saving");
    setError(null);
    try {
      await createUser({
        email: form.email.trim(),
        full_name: form.full_name.trim(),
        password: form.password,
        role: form.role,
      });
      setForm(initialCreateForm);
      await onCreated();
    } catch (requestError) {
      setError(userErrorMessage(requestError, "User could not be created. Try again."));
      setForm((current) => ({ ...current, password: "" }));
    } finally {
      setState("idle");
    }
  }

  return (
    <form className="user-admin-form" onSubmit={submit}>
      <div className="form-heading">
        <div><p className="section-kicker">New account</p><h2>Create user</h2></div>
        <span>POST /api/users</span>
      </div>
      <div className="user-form-grid">
        <label>Full name<input required minLength={1} maxLength={255} value={form.full_name} onChange={(event) => setForm((current) => ({ ...current, full_name: event.target.value }))} /></label>
        <label>Email<input required type="email" value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} /></label>
        <label>Password<input required type="password" minLength={12} autoComplete="new-password" value={form.password} onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))} /></label>
        <label>Role<RoleSelect value={form.role} onChange={(role) => setForm((current) => ({ ...current, role }))} /></label>
      </div>
      {error && <p className="alert-action-error" role="alert">{error}</p>}
      <div className="form-actions">
        <button type="button" className="quiet-button" onClick={onCancel}>Cancel</button>
        <button type="submit" className="primary-button" disabled={state === "saving"}>{state === "saving" ? "Creating..." : "Create User"}</button>
      </div>
    </form>
  );
}

function EditUserPanel({
  selectedUser,
  currentUserId,
  onSaved,
  onCancel,
}: {
  selectedUser: User;
  currentUserId: string;
  onSaved: () => Promise<void>;
  onCancel: () => void;
}) {
  const isSelf = selectedUser.id === currentUserId;
  const [fullName, setFullName] = useState(selectedUser.full_name);
  const [role, setRole] = useState<UserRole>(selectedUser.role);
  const [isActive, setIsActive] = useState(selectedUser.is_active);
  const [state, setState] = useState<SaveState>("idle");
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!fullName.trim()) return;

    const input: UserUpdateInput = { full_name: fullName.trim() };
    if (!isSelf) {
      input.role = role;
      input.is_active = isActive;
    }

    setState("saving");
    setError(null);
    try {
      await updateUser(selectedUser.id, input);
      await onSaved();
    } catch (requestError) {
      setError(userErrorMessage(requestError, "User could not be updated. Try again."));
    } finally {
      setState("idle");
    }
  }

  return (
    <form className="user-admin-form user-edit-form" onSubmit={submit}>
      <div className="form-heading">
        <div><p className="section-kicker">Account settings</p><h2>Edit user</h2></div>
        <span>PATCH /api/users/{selectedUser.id}</span>
      </div>
      <div className="user-form-grid">
        <label className="form-field-wide">Full name<input required minLength={1} maxLength={255} value={fullName} onChange={(event) => setFullName(event.target.value)} /></label>
        {isSelf ? (
          <div className="self-protection-note form-field-wide">
            <strong>Your account is protected</strong>
            <span>Role and active status changes are not offered for the signed-in admin account.</span>
          </div>
        ) : (
          <>
            <label>Role<RoleSelect value={role} onChange={setRole} /></label>
            <label className="user-toggle-field"><span>Account status</span><span><input type="checkbox" checked={isActive} onChange={(event) => setIsActive(event.target.checked)} /> Active account</span></label>
          </>
        )}
      </div>
      {error && <p className="alert-action-error" role="alert">{error}</p>}
      <div className="form-actions">
        <button type="button" className="quiet-button" onClick={onCancel}>Cancel</button>
        <button type="submit" className="primary-button" disabled={state === "saving"}>{state === "saving" ? "Saving..." : "Save User"}</button>
      </div>
    </form>
  );
}

function RouteState({ title, detail }: { title: string; detail: string }) {
  return (
    <section className="content-section admin-users-page">
      <div className="detail-state"><strong>{title}</strong><p>{detail}</p></div>
    </section>
  );
}

export default function AdminUsersPage() {
  const router = useRouter();
  const { user, isLoading } = useSession();
  const isAdmin = hasPermission(user, "administerUsers");
  const [users, setUsers] = useState<User[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);

  useEffect(() => {
    if (isLoading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    if (!isAdmin) router.replace("/");
  }, [isAdmin, isLoading, router, user]);

  const loadUsers = useCallback(async () => {
    setLoadState("loading");
    setError(null);
    try {
      const loadedUsers = await getUsers();
      setUsers(loadedUsers);
      setLoadState("ready");
    } catch (loadError) {
      setLoadState("error");
      setError(userErrorMessage(loadError, "Users could not be loaded."));
    }
  }, []);

  useEffect(() => {
    if (!isAdmin) return;
    let mounted = true;

    async function loadInitialUsers() {
      try {
        const loadedUsers = await getUsers();
        if (!mounted) return;
        setUsers(loadedUsers);
        setLoadState("ready");
        setError(null);
      } catch (loadError) {
        if (!mounted) return;
        setLoadState("error");
        setError(userErrorMessage(loadError, "Users could not be loaded."));
      }
    }

    void loadInitialUsers();
    return () => { mounted = false; };
  }, [isAdmin]);

  const counts = useMemo(() => ({
    total: users.length,
    active: users.filter((item) => item.is_active).length,
    inactive: users.filter((item) => !item.is_active).length,
    admins: users.filter((item) => hasPermission(item.role, "administerUsers")).length,
  }), [users]);

  async function handleCreated() {
    await loadUsers();
    setIsCreating(false);
    setNotice("User created.");
  }

  async function handleSaved() {
    await loadUsers();
    setEditingUser(null);
    setNotice("User updated.");
  }

  if (isLoading) return <RouteState title="Checking access" detail="Verifying your AssetGuard session." />;
  if (!user) return <RouteState title="Session required" detail="Redirecting to sign in." />;
  if (!isAdmin) return <RouteState title="Access denied" detail="Redirecting to the operations overview." />;

  return (
    <section className="content-section admin-users-page">
      <div className="workspace-intro">
        <div>
          <p className="section-kicker">Admin workspace</p>
          <h2>User management</h2>
          <p className="intro-copy">Create accounts, review access, and maintain operational roles.</p>
        </div>
        <div className="workspace-actions">
          <span className="data-badge">ADMIN ONLY</span>
          <button type="button" className="primary-small-button" onClick={() => { setIsCreating((current) => !current); setEditingUser(null); setNotice(null); }}>{isCreating ? "Close Creator" : "Create User"}</button>
        </div>
      </div>

      <div className="user-count-grid" aria-label="User summary">
        <div><span>Total</span><strong>{counts.total}</strong></div>
        <div><span>Active</span><strong>{counts.active}</strong></div>
        <div><span>Inactive</span><strong>{counts.inactive}</strong></div>
        <div><span>Admins</span><strong>{counts.admins}</strong></div>
      </div>

      {notice && <div className="action-success user-admin-notice" role="status">{notice}</div>}
      {isCreating && <CreateUserPanel onCreated={handleCreated} onCancel={() => setIsCreating(false)} />}
      {editingUser && <EditUserPanel key={editingUser.id} selectedUser={editingUser} currentUserId={user.id} onSaved={handleSaved} onCancel={() => setEditingUser(null)} />}

      <section className="user-register">
        <div className="alert-register-heading">
          <div><p className="section-kicker">User register</p><h3>{users.length} {users.length === 1 ? "account" : "accounts"}</h3></div>
          <div className="filter-status">{loadState === "loading" ? "Updating register" : "Live register"}</div>
        </div>
        {error && <div className="alert-workspace-notice" role="alert">{error}</div>}
        {loadState === "loading" && <RecordSkeletons />}
        {loadState !== "loading" && users.length === 0 && <div className="detail-state"><strong>No users found</strong><p>Create the first managed account when the backend is ready.</p></div>}
        {users.length > 0 && (
          <div className="user-table-wrap">
            <div className="user-table" role="table" aria-label="Users">
              <div className="user-row user-row-header" role="row"><span>User</span><span>Role</span><span>Status</span><span>Last login</span><span>Created</span><span>Action</span></div>
              {users.map((item) => {
                const isSelf = item.id === user.id;
                return (
                  <div className="user-row user-row-data" role="row" key={item.id}>
                    <span className="user-primary"><strong>{item.full_name}{isSelf && <em>You</em>}</strong><small>{item.email}</small></span>
                    <span className="role-chip">{ROLE_LABELS[item.role]}</span>
                    <span><StatusBadge value={item.is_active ? "active" : "inactive"} /></span>
                    <span>{formatDateTime(item.last_login_at)}</span>
                    <span>{formatDateTime(item.created_at)}</span>
                    <span><button type="button" className="quiet-button" onClick={() => { setEditingUser(item); setIsCreating(false); setNotice(null); }}>Edit</button></span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </section>
    </section>
  );
}
