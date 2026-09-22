export const EMPTY_VALUE = "--";

export function formatLabel(value: string) {
  return value.replace(/_/g, " ");
}

export function formatDateTime(value: string | null, emptyValue = EMPTY_VALUE) {
  if (!value) return emptyValue;

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return emptyValue;

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function formatSensorValue(value: number | null, unit: string) {
  if (value === null) return EMPTY_VALUE;

  return `${new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(value)} ${unit}`;
}
