const DATE_ONLY_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const DATETIME_PATTERN = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d{1,6})?)?$/;
const HAS_TIMEZONE_PATTERN = /(Z|[+-]\d{2}:\d{2})$/i;

function normalizeBackendTime(value: string): string {
  const trimmed = value.trim();

  if (DATE_ONLY_PATTERN.test(trimmed)) {
    return `${trimmed}T00:00:00`;
  }

  const normalized = trimmed.replace(" ", "T");
  if (DATETIME_PATTERN.test(normalized) && !HAS_TIMEZONE_PATTERN.test(normalized)) {
    // Backend stores UTC timestamps without timezone suffix.
    // Force UTC interpretation to avoid browser-local parsing drift.
    return `${normalized}Z`;
  }

  return normalized;
}

function parseBackendDateTime(value: string | null | undefined): Date | null {
  if (!value) return null;
  const normalized = normalizeBackendTime(value);
  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return parsed;
}

export function toEpochMillis(value: string | null | undefined): number {
  const parsed = parseBackendDateTime(value);
  return parsed ? parsed.getTime() : Number.NaN;
}

export function formatDateTimeInBrowserTimeZone(value: string | null | undefined): string {
  if (!value) return "-";
  const parsed = parseBackendDateTime(value);
  if (!parsed) return value;
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(parsed);
}

export function todayInBrowserTimeZone(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}
