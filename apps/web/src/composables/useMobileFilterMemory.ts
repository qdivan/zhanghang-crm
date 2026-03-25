import { ref } from "vue";

type FilterPrimitive = string | number | boolean | null;
type FilterShape = Record<string, FilterPrimitive>;

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function normalizeSnapshot<T extends FilterShape>(defaults: T, raw: unknown): T | null {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    return null;
  }

  const next = { ...defaults };
  let hasValue = false;

  for (const key of Object.keys(defaults) as Array<keyof T>) {
    const fallback = defaults[key];
    const value = (raw as Record<string, unknown>)[String(key)];

    if (typeof fallback === "string") {
      if (typeof value === "string") {
        next[key] = value as T[keyof T];
        hasValue = true;
      }
      continue;
    }

    if (typeof fallback === "number") {
      if (typeof value === "number" && Number.isFinite(value)) {
        next[key] = value as T[keyof T];
        hasValue = true;
      }
      continue;
    }

    if (typeof fallback === "boolean") {
      if (typeof value === "boolean") {
        next[key] = value as T[keyof T];
        hasValue = true;
      }
      continue;
    }

    if (
      value === null ||
      typeof value === "string" ||
      (typeof value === "number" && Number.isFinite(value)) ||
      typeof value === "boolean"
    ) {
      next[key] = value as T[keyof T];
      hasValue = true;
    }
  }

  return hasValue ? next : null;
}

function hasMeaningfulState<T extends FilterShape>(snapshot: T, defaults: T): boolean {
  for (const key of Object.keys(defaults) as Array<keyof T>) {
    const value = snapshot[key];
    if (value === defaults[key]) continue;
    if (value === "" || value === null) continue;
    return true;
  }
  return false;
}

export function useMobileFilterMemory<T extends FilterShape>(storageKey: string, defaults: T) {
  const defaultSnapshot = { ...defaults };
  const hasSavedState = ref(false);

  function readSnapshot(): T | null {
    if (!canUseStorage()) {
      hasSavedState.value = false;
      return null;
    }

    const raw = window.localStorage.getItem(storageKey);
    if (!raw) {
      hasSavedState.value = false;
      return null;
    }

    try {
      const parsed = JSON.parse(raw);
      const snapshot = normalizeSnapshot(defaultSnapshot, parsed);
      if (!snapshot || !hasMeaningfulState(snapshot, defaultSnapshot)) {
        window.localStorage.removeItem(storageKey);
        hasSavedState.value = false;
        return null;
      }
      hasSavedState.value = true;
      return snapshot;
    } catch {
      window.localStorage.removeItem(storageKey);
      hasSavedState.value = false;
      return null;
    }
  }

  function restoreSavedState(apply: (snapshot: T) => void): boolean {
    const snapshot = readSnapshot();
    if (!snapshot) return false;
    apply({ ...defaultSnapshot, ...snapshot });
    hasSavedState.value = true;
    return true;
  }

  function saveState(snapshot: T) {
    if (!canUseStorage()) return;

    const next = { ...defaultSnapshot, ...snapshot };
    if (!hasMeaningfulState(next, defaultSnapshot)) {
      window.localStorage.removeItem(storageKey);
      hasSavedState.value = false;
      return;
    }

    window.localStorage.setItem(storageKey, JSON.stringify(next));
    hasSavedState.value = true;
  }

  function clearState() {
    if (!canUseStorage()) return;
    window.localStorage.removeItem(storageKey);
    hasSavedState.value = false;
  }

  if (canUseStorage()) {
    void readSnapshot();
  }

  return {
    hasSavedState,
    restoreSavedState,
    saveState,
    clearState,
  };
}
