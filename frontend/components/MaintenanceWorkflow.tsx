"use client";

import { useMemo, useState, type FormEvent } from "react";
import {
  ApiError,
  cancelMaintenance,
  completeMaintenance,
  createMaintenanceRecord,
  startMaintenance,
  updateMaintenanceRecord,
} from "@/lib/api/client";
import { StatusBadge } from "@/components/StatusBadge";
import { formatDateTime } from "@/lib/format";
import { useSession } from "@/lib/auth/SessionContext";
import { hasPermission, PERMISSION_DENIED_MESSAGE } from "@/lib/auth/permissions";
import type {
  Asset,
  MaintenanceCancelInput,
  MaintenanceCompleteInput,
  MaintenanceCreateInput,
  MaintenanceRecord,
  MaintenanceStartInput,
  MaintenanceType,
  MaintenanceUpdateInput,
} from "@/lib/api/types";

type RecordAction = "starting" | "completing" | "cancelling" | "saving";
type ActivePanel = "start" | "complete" | "cancel" | "edit";

export const maintenanceTypes: MaintenanceType[] = ["preventive", "predictive", "corrective", "inspection"];

const typeLabels: Record<MaintenanceType, string> = {
  preventive: "Preventive",
  predictive: "Predictive",
  corrective: "Corrective",
  inspection: "Inspection",
};

function optionalText(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : undefined;
}

function optionalNullableText(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function toDateTimeLocalValue(value: string | null) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";

  const offsetDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return offsetDate.toISOString().slice(0, 16);
}

function fromDateTimeLocalValue(value: string) {
  if (!value) return undefined;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return undefined;

  return date.toISOString();
}

export function maintenanceErrorMessage(error: unknown, fallback: string) {
  if (error instanceof ApiError) {
    if (error.status === 404) return "This maintenance record or asset no longer exists.";
    if (error.status === 403) return PERMISSION_DENIED_MESSAGE;
    if (error.status === 409) return "This maintenance action is not allowed in the current workflow state.";
    if (error.status === 422) return "The submitted maintenance information is invalid.";
    return error.message || fallback;
  }

  if (error instanceof TypeError) return "The maintenance request could not reach the backend.";

  return fallback;
}

export function MaintenanceEmptyState({
  hasRecords,
  onSchedule,
  canSchedule = true,
}: {
  hasRecords: boolean;
  onSchedule?: () => void;
  canSchedule?: boolean;
}) {
  return <div className="maintenance-empty-state"><div><strong>{hasRecords ? "No matching maintenance records." : "No maintenance records."}</strong><p>{hasRecords ? "Adjust the filters to see other reliability work." : "No maintenance work has been recorded yet."}</p></div>{!hasRecords && onSchedule && canSchedule && <button type="button" className="primary-small-button" onClick={onSchedule}>Schedule Maintenance</button>}</div>;
}

export function CreateMaintenanceForm({
  assets,
  defaultAssetId,
  lockAsset = false,
  onCreated,
  onCancel,
}: {
  assets: Asset[];
  defaultAssetId?: string;
  lockAsset?: boolean;
  onCreated: (record: MaintenanceRecord) => void;
  onCancel?: () => void;
}) {
  const initialAssetId = defaultAssetId ?? assets[0]?.id ?? "";
  const [assetId, setAssetId] = useState(initialAssetId);
  const [maintenanceType, setMaintenanceType] = useState<MaintenanceType>("inspection");
  const [description, setDescription] = useState("");
  const [scheduledFor, setScheduledFor] = useState("");
  const [engineerName, setEngineerName] = useState("");
  const [state, setState] = useState<"idle" | "creating">("idle");
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!assetId || !description.trim()) return;

    const input: MaintenanceCreateInput = {
      maintenance_type: maintenanceType,
      description: description.trim(),
      ...(fromDateTimeLocalValue(scheduledFor) ? { scheduled_for: fromDateTimeLocalValue(scheduledFor) } : {}),
      ...(optionalText(engineerName) ? { engineer_name: optionalText(engineerName) } : {}),
    };

    setState("creating");
    setError(null);
    try {
      const record = await createMaintenanceRecord(assetId, input);
      onCreated(record);
      setDescription("");
      setScheduledFor("");
      setEngineerName("");
      setMaintenanceType("inspection");
    } catch (requestError) {
      setError(maintenanceErrorMessage(requestError, "Maintenance could not be scheduled. Try again."));
    } finally {
      setState("idle");
    }
  }

  return <form className="create-maintenance-form" onSubmit={submit}><div className="form-heading"><div><p className="section-kicker">Planned work</p><h2>Schedule maintenance</h2></div><span>Backend sets planned status</span></div><div className="maintenance-form-grid"><label>Asset<select required value={assetId} disabled={lockAsset} onChange={(event) => setAssetId(event.target.value)}><option value="" disabled>Select an asset</option>{assets.map((asset) => <option value={asset.id} key={asset.id}>{asset.name} - {asset.asset_code}</option>)}</select></label><label>Type<select value={maintenanceType} onChange={(event) => setMaintenanceType(event.target.value as MaintenanceType)}>{maintenanceTypes.map((type) => <option value={type} key={type}>{typeLabels[type]}</option>)}</select></label><label>Scheduled for<input type="datetime-local" value={scheduledFor} onChange={(event) => setScheduledFor(event.target.value)} /></label><label>Engineer<input value={engineerName} onChange={(event) => setEngineerName(event.target.value)} placeholder="Optional" /></label><label className="form-field-wide">Description<textarea required value={description} onChange={(event) => setDescription(event.target.value)} rows={3} placeholder="Describe the planned work" /></label></div>{error && <p className="alert-action-error" role="alert">{error}</p>}<div className="form-actions">{onCancel && <button type="button" className="quiet-button" onClick={onCancel}>Cancel</button>}<button type="submit" className="primary-button" disabled={state === "creating" || assets.length === 0}>{state === "creating" ? "Scheduling..." : "Schedule Maintenance"}</button></div></form>;
}

function RecordFacts({ record }: { record: MaintenanceRecord }) {
  const facts = [
    ["Scheduled", record.scheduled_for ? formatDateTime(record.scheduled_for) : null],
    ["Started", record.started_at ? formatDateTime(record.started_at) : null],
    ["Completed", record.completed_at ? formatDateTime(record.completed_at) : null],
    ["Engineer", record.engineer_name],
    ["Outcome", record.outcome],
    ["Created", formatDateTime(record.created_at)],
    ["Updated", formatDateTime(record.updated_at)],
  ].filter(([, value]) => value);

  return <dl className="record-details maintenance-record-details">{facts.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>;
}

function EditRecordPanel({
  record,
  action,
  onSave,
  onClose,
}: {
  record: MaintenanceRecord;
  action?: RecordAction;
  onSave: (input: MaintenanceUpdateInput) => Promise<void>;
  onClose: () => void;
}) {
  const [maintenanceType, setMaintenanceType] = useState<MaintenanceType>(record.maintenance_type);
  const [description, setDescription] = useState(record.description);
  const [scheduledFor, setScheduledFor] = useState(toDateTimeLocalValue(record.scheduled_for));
  const [engineerName, setEngineerName] = useState(record.engineer_name ?? "");
  const [outcome, setOutcome] = useState(record.outcome ?? "");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!description.trim()) return;

    await onSave({
      maintenance_type: maintenanceType,
      description: description.trim(),
      scheduled_for: scheduledFor ? fromDateTimeLocalValue(scheduledFor) ?? null : null,
      engineer_name: optionalNullableText(engineerName),
      outcome: optionalNullableText(outcome),
    });
  }

  return <form className="maintenance-action-panel maintenance-edit-panel" onSubmit={submit}><div className="maintenance-action-heading"><strong>Edit planning details</strong><button type="button" className="text-button" onClick={onClose}>Close</button></div><div className="maintenance-inline-grid"><label>Type<select value={maintenanceType} onChange={(event) => setMaintenanceType(event.target.value as MaintenanceType)}>{maintenanceTypes.map((type) => <option value={type} key={type}>{typeLabels[type]}</option>)}</select></label><label>Scheduled for<input type="datetime-local" value={scheduledFor} onChange={(event) => setScheduledFor(event.target.value)} /></label><label>Engineer<input value={engineerName} onChange={(event) => setEngineerName(event.target.value)} placeholder="Optional" /></label><label>Outcome<input value={outcome} onChange={(event) => setOutcome(event.target.value)} placeholder="Optional" /></label><label className="form-field-wide">Description<textarea required rows={2} value={description} onChange={(event) => setDescription(event.target.value)} /></label></div><div className="notes-editor-actions"><button type="button" className="quiet-button" onClick={onClose}>Cancel</button><button type="submit" className="primary-small-button" disabled={action === "saving"}>{action === "saving" ? "Saving..." : "Save Details"}</button></div></form>;
}

function StartPanel({
  record,
  action,
  onStart,
  onClose,
}: {
  record: MaintenanceRecord;
  action?: RecordAction;
  onStart: (input: MaintenanceStartInput) => Promise<void>;
  onClose: () => void;
}) {
  const [engineerName, setEngineerName] = useState(record.engineer_name ?? "");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onStart({ ...(optionalText(engineerName) ? { engineer_name: optionalText(engineerName) } : {}) });
  }

  return <form className="maintenance-action-panel" onSubmit={submit}><div className="maintenance-action-heading"><strong>Start maintenance</strong><button type="button" className="text-button" onClick={onClose}>Close</button></div><label>Engineer<input value={engineerName} onChange={(event) => setEngineerName(event.target.value)} placeholder="Optional" /></label><div className="notes-editor-actions"><button type="button" className="quiet-button" onClick={onClose}>Cancel</button><button type="submit" className="primary-small-button" disabled={action === "starting"}>{action === "starting" ? "Starting..." : "Start Maintenance"}</button></div></form>;
}

function CompletePanel({
  record,
  action,
  onComplete,
  onClose,
}: {
  record: MaintenanceRecord;
  action?: RecordAction;
  onComplete: (input: MaintenanceCompleteInput) => Promise<void>;
  onClose: () => void;
}) {
  const [outcome, setOutcome] = useState(record.outcome ?? "");
  const [engineerName, setEngineerName] = useState(record.engineer_name ?? "");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onComplete({
      ...(optionalText(outcome) ? { outcome: optionalText(outcome) } : {}),
      ...(optionalText(engineerName) ? { engineer_name: optionalText(engineerName) } : {}),
    });
  }

  return <form className="maintenance-action-panel" onSubmit={submit}><div className="maintenance-action-heading"><strong>Complete maintenance</strong><button type="button" className="text-button" onClick={onClose}>Close</button></div><div className="maintenance-inline-grid"><label className="form-field-wide">Outcome<textarea rows={3} value={outcome} onChange={(event) => setOutcome(event.target.value)} placeholder="Optional completion notes" /></label><label className="form-field-wide">Engineer<input value={engineerName} onChange={(event) => setEngineerName(event.target.value)} placeholder="Optional" /></label></div><div className="notes-editor-actions"><button type="button" className="quiet-button" onClick={onClose}>Cancel</button><button type="submit" className="primary-small-button" disabled={action === "completing"}>{action === "completing" ? "Completing..." : "Complete Maintenance"}</button></div></form>;
}

function CancelPanel({
  record,
  action,
  onCancelRecord,
  onClose,
}: {
  record: MaintenanceRecord;
  action?: RecordAction;
  onCancelRecord: (input: MaintenanceCancelInput) => Promise<void>;
  onClose: () => void;
}) {
  const [outcome, setOutcome] = useState(record.outcome ?? "");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onCancelRecord({ ...(optionalText(outcome) ? { outcome: optionalText(outcome) } : {}) });
  }

  return <form className="maintenance-action-panel" onSubmit={submit}><div className="maintenance-action-heading"><strong>Cancel maintenance</strong><button type="button" className="text-button" onClick={onClose}>Close</button></div><label>Reason / outcome<textarea rows={3} value={outcome} onChange={(event) => setOutcome(event.target.value)} placeholder="Optional reason" /></label><div className="notes-editor-actions"><button type="button" className="quiet-button" onClick={onClose}>Keep Work</button><button type="submit" className="primary-small-button" disabled={action === "cancelling"}>{action === "cancelling" ? "Cancelling..." : "Cancel Maintenance"}</button></div></form>;
}

export function MaintenanceRecordList({
  records,
  assets,
  showAsset = true,
  onRecordChange,
}: {
  records: MaintenanceRecord[];
  assets: Asset[];
  showAsset?: boolean;
  onRecordChange?: (record: MaintenanceRecord) => void;
}) {
  const { user } = useSession();
  const [actions, setActions] = useState<Record<string, RecordAction | undefined>>({});
  const [panels, setPanels] = useState<Record<string, ActivePanel | undefined>>({});
  const [errors, setErrors] = useState<Record<string, string | undefined>>({});
  const [successes, setSuccesses] = useState<Record<string, string | undefined>>({});
  const assetById = useMemo(() => new Map(assets.map((asset) => [asset.id, asset])), [assets]);
  const canEditMaintenance = hasPermission(user, "editMaintenance");
  const canStartMaintenance = hasPermission(user, "startMaintenance");
  const canCompleteMaintenance = hasPermission(user, "completeMaintenance");
  const canCancelMaintenance = hasPermission(user, "cancelMaintenance");

  function closePanel(recordId: string) {
    setPanels((current) => ({ ...current, [recordId]: undefined }));
  }

  function replaceRecord(record: MaintenanceRecord) {
    setErrors((current) => ({ ...current, [record.id]: undefined }));
    closePanel(record.id);
    onRecordChange?.(record);
  }

  async function runAction(record: MaintenanceRecord, action: RecordAction, callback: () => Promise<MaintenanceRecord>) {
    setActions((current) => ({ ...current, [record.id]: action }));
    setErrors((current) => ({ ...current, [record.id]: undefined }));
    setSuccesses((current) => ({ ...current, [record.id]: undefined }));
    try {
      replaceRecord(await callback());
      setSuccesses((current) => ({ ...current, [record.id]: `${action === "saving" ? "Maintenance details saved" : action === "starting" ? "Maintenance started" : action === "completing" ? "Maintenance completed" : "Maintenance cancelled"}.` }));
    } catch (error) {
      setErrors((current) => ({ ...current, [record.id]: maintenanceErrorMessage(error, "Maintenance action failed. Try again.") }));
    } finally {
      setActions((current) => ({ ...current, [record.id]: undefined }));
    }
  }

  return (
    <div className="maintenance-record-list">
      {records.map((record) => {
        const asset = assetById.get(record.asset_id);
        const action = actions[record.id];
        const activePanel = panels[record.id];
        const canStart = canStartMaintenance && record.status === "planned";
        const canComplete = canCompleteMaintenance && record.status === "in_progress";
        const canCancel = canCancelMaintenance && (record.status === "planned" || record.status === "in_progress");
        const hasActions = canEditMaintenance || canStart || canComplete || canCancel;

        return (
          <article className="maintenance-record" key={record.id}>
            <div className="record-card-heading">
              <div>
                <h4>{record.description}</h4>
                {showAsset && asset && <p className="alert-asset-link">{asset.name} - {asset.asset_code}</p>}
              </div>
              <div>
                <StatusBadge value={record.maintenance_type} kind="maintenance" />
                <StatusBadge value={record.status} />
              </div>
            </div>

            <RecordFacts record={record} />

            {errors[record.id] && <p className="alert-action-error" role="alert">{errors[record.id]}</p>}
            {successes[record.id] && <p className="action-success" role="status">{successes[record.id]}</p>}

            {hasActions && <div className="maintenance-actions">
              {canEditMaintenance && (
                <button
                  type="button"
                  className="quiet-button"
                  disabled={Boolean(action)}
                  onClick={() => setPanels((current) => ({
                    ...current,
                    [record.id]: current[record.id] === "edit" ? undefined : "edit",
                  }))}
                >
                  Edit Details
                </button>
              )}
              {canStart && (
                <button
                  type="button"
                  className="primary-small-button"
                  disabled={Boolean(action)}
                  onClick={() => setPanels((current) => ({
                    ...current,
                    [record.id]: current[record.id] === "start" ? undefined : "start",
                  }))}
                >
                  Start Maintenance
                </button>
              )}
              {canComplete && (
                <button
                  type="button"
                  className="primary-small-button"
                  disabled={Boolean(action)}
                  onClick={() => setPanels((current) => ({
                    ...current,
                    [record.id]: current[record.id] === "complete" ? undefined : "complete",
                  }))}
                >
                  Complete Maintenance
                </button>
              )}
              {canCancel && (
                <button
                  type="button"
                  className="quiet-button terminal-button"
                  disabled={Boolean(action)}
                  onClick={() => setPanels((current) => ({
                    ...current,
                    [record.id]: current[record.id] === "cancel" ? undefined : "cancel",
                  }))}
                >
                  Cancel Maintenance
                </button>
              )}
            </div>}

            {activePanel === "edit" && canEditMaintenance && (
              <EditRecordPanel
                record={record}
                action={action}
                onClose={() => closePanel(record.id)}
                onSave={(input) => runAction(record, "saving", () => updateMaintenanceRecord(record.id, input))}
              />
            )}
            {activePanel === "start" && canStart && (
              <StartPanel
                record={record}
                action={action}
                onClose={() => closePanel(record.id)}
                onStart={(input) => runAction(record, "starting", () => startMaintenance(record.id, input))}
              />
            )}
            {activePanel === "complete" && canComplete && (
              <CompletePanel
                record={record}
                action={action}
                onClose={() => closePanel(record.id)}
                onComplete={(input) => runAction(record, "completing", () => completeMaintenance(record.id, input))}
              />
            )}
            {activePanel === "cancel" && canCancel && (
              <CancelPanel
                record={record}
                action={action}
                onClose={() => closePanel(record.id)}
                onCancelRecord={(input) => runAction(record, "cancelling", () => cancelMaintenance(record.id, input))}
              />
            )}
          </article>
        );
      })}
    </div>
  );
}
