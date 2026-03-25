import { isHandsetViewport } from "./config";

const MOBILE_PERFORMANCE_STORAGE_KEY = "crm.mobile-performance";
const MOBILE_PERFORMANCE_UPDATE_EVENT = "crm:mobile-performance:update";
const MAX_MOBILE_PERFORMANCE_ENTRIES = 20;
const STALE_PENDING_MEASUREMENT_MS = 30_000;

export type MobilePerformanceEntryKind = "login_to_todo" | "primary_nav";

export type MobilePerformanceEntry = {
  id: string;
  kind: MobilePerformanceEntryKind;
  label: string;
  sourceLabel: string;
  sourcePath: string;
  targetLabel: string;
  targetPath: string;
  durationMs: number;
  recordedAt: string;
};

type PendingMeasurement = {
  id: string;
  kind: MobilePerformanceEntryKind;
  label: string;
  sourceLabel: string;
  sourcePath: string;
  targetLabel: string;
  targetPath: string;
  startedAt: number;
  startMark: string;
  endMark: string;
};

const pendingMeasurements = new Map<string, PendingMeasurement>();
let measurementSequence = 0;

function supportsMobilePerformanceMeasurement(): boolean {
  return typeof window !== "undefined" && typeof performance !== "undefined" && isHandsetViewport();
}

function normalizePath(path: string): string {
  const [pathname = "/"] = String(path || "/").split("?");
  if (!pathname) return "/";
  if (pathname.length > 1) {
    return pathname.replace(/\/+$/, "");
  }
  return pathname;
}

function runAfterNextPaint(callback: () => void) {
  if (typeof window === "undefined") {
    callback();
    return;
  }

  const runner = window.requestAnimationFrame
    ? () => window.requestAnimationFrame(() => window.requestAnimationFrame(callback))
    : () => window.setTimeout(callback, 34);

  runner();
}

function readEntriesFromStorage(): MobilePerformanceEntry[] {
  if (typeof window === "undefined") return [];

  try {
    const raw = window.sessionStorage.getItem(MOBILE_PERFORMANCE_STORAGE_KEY);
    if (!raw) return [];

    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function emitEntries(entries: MobilePerformanceEntry[]) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent<MobilePerformanceEntry[]>(MOBILE_PERFORMANCE_UPDATE_EVENT, {
    detail: entries,
  }));
}

function persistEntries(entries: MobilePerformanceEntry[]) {
  if (typeof window === "undefined") return;

  try {
    window.sessionStorage.setItem(MOBILE_PERFORMANCE_STORAGE_KEY, JSON.stringify(entries.slice(-MAX_MOBILE_PERFORMANCE_ENTRIES)));
  } catch {
    return;
  }

  emitEntries(entries.slice(-MAX_MOBILE_PERFORMANCE_ENTRIES));
}

function pruneStaleMeasurements(now = performance.now()) {
  for (const [id, measurement] of pendingMeasurements) {
    if (now - measurement.startedAt > STALE_PENDING_MEASUREMENT_MS) {
      pendingMeasurements.delete(id);
      performance.clearMarks(measurement.startMark);
      performance.clearMarks(measurement.endMark);
    }
  }
}

function beginMeasurement(payload: Omit<PendingMeasurement, "id" | "startedAt" | "startMark" | "endMark">) {
  if (!supportsMobilePerformanceMeasurement()) return;

  pruneStaleMeasurements();

  measurementSequence += 1;
  const id = `${payload.kind}:${Date.now()}:${measurementSequence}`;
  const startMark = `${id}:start`;
  const endMark = `${id}:end`;

  performance.mark(startMark);
  pendingMeasurements.set(id, {
    ...payload,
    id,
    startedAt: performance.now(),
    startMark,
    endMark,
  });
}

export function startMobileLoginToTodoMeasurement() {
  beginMeasurement({
    kind: "login_to_todo",
    label: "登录 -> Todo",
    sourceLabel: "登录",
    sourcePath: "/login",
    targetLabel: "Todo",
    targetPath: "/m/todo",
  });
}

export function startMobilePrimaryNavMeasurement(payload: {
  sourceLabel: string;
  sourcePath: string;
  targetLabel: string;
  targetPath: string;
}) {
  if (normalizePath(payload.sourcePath) === normalizePath(payload.targetPath)) return;

  beginMeasurement({
    kind: "primary_nav",
    label: `${payload.sourceLabel} -> ${payload.targetLabel}`,
    sourceLabel: payload.sourceLabel,
    sourcePath: payload.sourcePath,
    targetLabel: payload.targetLabel,
    targetPath: payload.targetPath,
  });
}

function finalizeMeasurement(measurement: PendingMeasurement) {
  pendingMeasurements.delete(measurement.id);

  runAfterNextPaint(() => {
    performance.mark(measurement.endMark);
    performance.measure(measurement.label, measurement.startMark, measurement.endMark);

    const durationMs = Math.max(0, performance.now() - measurement.startedAt);
    const nextEntry: MobilePerformanceEntry = {
      id: measurement.id,
      kind: measurement.kind,
      label: measurement.label,
      sourceLabel: measurement.sourceLabel,
      sourcePath: normalizePath(measurement.sourcePath),
      targetLabel: measurement.targetLabel,
      targetPath: normalizePath(measurement.targetPath),
      durationMs,
      recordedAt: new Date().toISOString(),
    };

    const nextEntries = [...readEntriesFromStorage(), nextEntry].slice(-MAX_MOBILE_PERFORMANCE_ENTRIES);
    persistEntries(nextEntries);
    performance.clearMarks(measurement.startMark);
    performance.clearMarks(measurement.endMark);
  });
}

export function flushMobilePerformanceForRoute(path: string) {
  if (!supportsMobilePerformanceMeasurement()) return;

  const normalizedTargetPath = normalizePath(path);
  const matchedMeasurements = [...pendingMeasurements.values()].filter((measurement) => (
    normalizePath(measurement.targetPath) === normalizedTargetPath
  ));

  for (const measurement of matchedMeasurements) {
    finalizeMeasurement(measurement);
  }
}

export function readMobilePerformanceEntries(): MobilePerformanceEntry[] {
  return readEntriesFromStorage();
}

export function clearMobilePerformanceEntries() {
  if (typeof window === "undefined") return;

  try {
    window.sessionStorage.removeItem(MOBILE_PERFORMANCE_STORAGE_KEY);
  } catch {
    return;
  }

  emitEntries([]);
}

export function subscribeMobilePerformanceEntries(
  callback: (entries: MobilePerformanceEntry[]) => void,
): () => void {
  if (typeof window === "undefined") return () => {};

  const handler = (event: Event) => {
    const detail = (event as CustomEvent<MobilePerformanceEntry[]>).detail;
    callback(Array.isArray(detail) ? detail : readEntriesFromStorage());
  };

  window.addEventListener(MOBILE_PERFORMANCE_UPDATE_EVENT, handler as EventListener);
  return () => {
    window.removeEventListener(MOBILE_PERFORMANCE_UPDATE_EVENT, handler as EventListener);
  };
}
