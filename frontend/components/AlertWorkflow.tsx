"use client";

import { useState } from "react";
import {
  acknowledgeAlert,
  ApiError,
  createAlert,
  resolveAlert,
  updateAlert,
} from "@/lib/api/client";
import { StatusBadge } from "@/components/StatusBadge";
import { formatDateTime } from "@/lib/format";
import type { Alert, AlertCreateInput, AlertResolveInput, Asset } from "@/lib/api/types";

type AlertAction = "acknowledging" | "resolving" | "saving";

export function alertErrorMessage(error: unknown, fallback: string) {
  if (error instanceof ApiError) {
    if (error.status === 404) return "This alert or asset no longer exists.";
    if (error.status === 409) return error.message || "The alert has changed. Refresh and try again.";
    if (error.status === 422) return error.message || "Check the alert details and try again.";
    return error.message || fallback;
  }

  return fallback;
}

export function AlertList({
  alerts,
  assets,
  showAsset = true,
  onAlertChange,
}: {
  alerts: Alert[];
  assets: Asset[];
  showAsset?: boolean;
  onAlertChange?: (alert: Alert) => void;
}) {
  const [actions, setActions] = useState<Record<string, AlertAction | undefined>>({});
  const [notes, setNotes] = useState<Record<string, string>>(() => Object.fromEntries(alerts.map((alert) => [alert.id, alert.engineer_notes ?? ""])));
  const [editingNotes, setEditingNotes] = useState<Record<string, boolean>>({});
  const [errors, setErrors] = useState<Record<string, string | undefined>>({});
  const [successes, setSuccesses] = useState<Record<string, string | undefined>>({});
  const assetById = new Map(assets.map((asset) => [asset.id, asset]));

  function replaceAlert(alert: Alert) {
    setNotes((current) => ({ ...current, [alert.id]: alert.engineer_notes ?? "" }));
    setEditingNotes((current) => ({ ...current, [alert.id]: false }));
    setErrors((current) => ({ ...current, [alert.id]: undefined }));
    onAlertChange?.(alert);
  }

  async function runAction(alert: Alert, action: AlertAction, callback: () => Promise<Alert>) {
    setActions((current) => ({ ...current, [alert.id]: action }));
    setErrors((current) => ({ ...current, [alert.id]: undefined }));
    setSuccesses((current) => ({ ...current, [alert.id]: undefined }));
    try {
      replaceAlert(await callback());
      setSuccesses((current) => ({ ...current, [alert.id]: action === "saving" ? "Engineer notes saved." : action === "acknowledging" ? "Alert acknowledged." : "Alert resolved." }));
    } catch (error) {
      setErrors((current) => ({ ...current, [alert.id]: alertErrorMessage(error, "Alert action failed. Try again.") }));
    } finally {
      setActions((current) => ({ ...current, [alert.id]: undefined }));
    }
  }

  async function saveNotes(alert: Alert) {
    await runAction(alert, "saving", () => updateAlert(alert.id, { engineer_notes: notes[alert.id] ?? "" }));
  }

  return <div className="alert-record-list">{alerts.map((alert) => {
    const asset = assetById.get(alert.asset_id);
    const action = actions[alert.id];
    const isEditing = editingNotes[alert.id] === true;
    const canResolve = alert.status === "open" || alert.status === "acknowledged";

    return <article className="alert-record" key={alert.id}>
      <div className="alert-record-heading"><div><h3>{alert.title}</h3>{showAsset && asset && <p className="alert-asset-link">{asset.name} · {asset.asset_code}</p>}</div><div className="alert-badge-group"><StatusBadge value={alert.severity} kind="severity" /><StatusBadge value={alert.status} /></div></div>
      <div className="alert-record-body"><p>{alert.description || "No description provided."}</p><dl className="alert-record-facts"><div><dt>Detected</dt><dd>{formatDateTime(alert.detected_at)}</dd></div>{alert.acknowledged_at && <div><dt>Acknowledged</dt><dd>{formatDateTime(alert.acknowledged_at)}</dd></div>}{alert.resolved_at && <div><dt>Resolved</dt><dd>{formatDateTime(alert.resolved_at)}</dd></div>}</dl></div>
      <div className="alert-notes-area"><div className="alert-notes-heading"><span>Engineer notes</span>{!isEditing && <button type="button" className="text-button" onClick={() => setEditingNotes((current) => ({ ...current, [alert.id]: true }))}>{alert.engineer_notes ? "Edit" : "Add notes"}</button>}</div>{isEditing ? <div className="notes-editor"><textarea value={notes[alert.id] ?? ""} onChange={(event) => setNotes((current) => ({ ...current, [alert.id]: event.target.value }))} rows={2} placeholder="Add context for the next engineer" /><div className="notes-editor-actions"><button type="button" className="quiet-button" onClick={() => { setNotes((current) => ({ ...current, [alert.id]: alert.engineer_notes ?? "" })); setEditingNotes((current) => ({ ...current, [alert.id]: false })); }}>Cancel</button><button type="button" className="primary-small-button" disabled={action === "saving"} onClick={() => void saveNotes(alert)}>{action === "saving" ? "Saving..." : "Save notes"}</button></div></div> : <p className={alert.engineer_notes ? "alert-notes" : "alert-notes-empty"}>{alert.engineer_notes || "No engineer notes added."}</p>}</div>
      {errors[alert.id] && <p className="alert-action-error" role="alert">{errors[alert.id]}</p>}
      {successes[alert.id] && <p className="action-success" role="status">{successes[alert.id]}</p>}
      {(alert.status === "open" || canResolve) && <div className="alert-actions">{alert.status === "open" && <button type="button" className="quiet-button" disabled={Boolean(action)} onClick={() => void runAction(alert, "acknowledging", () => acknowledgeAlert(alert.id))}>{action === "acknowledging" ? "Acknowledging..." : "Acknowledge"}</button>}{canResolve && <button type="button" className="primary-small-button" disabled={Boolean(action)} onClick={() => void runAction(alert, "resolving", () => { const input: AlertResolveInput = { engineer_notes: notes[alert.id] ?? "" }; return resolveAlert(alert.id, input); })}>{action === "resolving" ? "Resolving..." : "Resolve"}</button>}</div>}
    </article>;
  })}</div>;
}

export function CreateAlertForm({ assets, onCreated }: { assets: Asset[]; onCreated: (alert: Alert) => void }) {
  const [assetId, setAssetId] = useState(assets[0]?.id ?? "");
  const [title, setTitle] = useState("");
  const [severity, setSeverity] = useState<AlertCreateInput["severity"]>("moderate");
  const [description, setDescription] = useState("");
  const [state, setState] = useState<"idle" | "creating">("idle");
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!assetId || !title.trim()) return;
    setState("creating");
    setError(null);
    try {
      const alert = await createAlert(assetId, { title: title.trim(), severity, ...(description.trim() ? { description: description.trim() } : {}) });
      onCreated(alert);
      setTitle("");
      setDescription("");
    } catch (requestError) {
      setError(alertErrorMessage(requestError, "Alert could not be created. Try again."));
    } finally {
      setState("idle");
    }
  }

  return <form className="create-alert-form" onSubmit={submit}><div className="form-heading"><div><p className="section-kicker">New signal</p><h2>Create alert</h2></div><span>Server controls status and timestamps</span></div><div className="alert-form-grid"><label>Asset<select required value={assetId} onChange={(event) => setAssetId(event.target.value)}><option value="" disabled>Select an asset</option>{assets.map((asset) => <option value={asset.id} key={asset.id}>{asset.name} · {asset.asset_code}</option>)}</select></label><label>Severity<select value={severity} onChange={(event) => setSeverity(event.target.value as AlertCreateInput["severity"])}><option value="low">Low</option><option value="moderate">Moderate</option><option value="high">High</option><option value="critical">Critical</option></select></label><label className="form-field-wide">Title<input required value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Describe the signal" /></label><label className="form-field-wide">Description<textarea value={description} onChange={(event) => setDescription(event.target.value)} rows={3} placeholder="Add useful context (optional)" /></label></div>{error && <p className="alert-action-error" role="alert">{error}</p>}<div className="form-actions"><button type="submit" className="primary-button" disabled={state === "creating" || assets.length === 0}>{state === "creating" ? "Creating..." : "Create alert"}</button></div></form>;
}
