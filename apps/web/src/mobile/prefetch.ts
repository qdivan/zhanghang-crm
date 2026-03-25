import type { MobileNavKey } from "./config";
import { isHandsetViewport } from "./config";

const PREFETCH_DELAY_MS = 180;
const IDLE_PREFETCH_TIMEOUT_MS = 1500;
const SECONDARY_PREFETCH_FALLBACK_DELAY_MS = 900;

type IdleCallbackHandle = number;
type IdleCallbackDeadline = {
  didTimeout: boolean;
  timeRemaining: () => number;
};

type IdleWindow = Window & {
  requestIdleCallback?: (callback: (deadline: IdleCallbackDeadline) => void, options?: { timeout: number }) => IdleCallbackHandle;
};

const mobileWorkspacePrefetchers = [
  () => import("../layouts/MobileLayout.vue"),
  () => import("../views/mobile/MobileTodoView.vue"),
  () => import("../views/LeadView.vue"),
  () => import("../views/BillingView.vue"),
];

const mobileSecondaryPrefetchers = [
  () => import("../views/CustomersView.vue"),
  () => import("../views/ReceiptReconciliationView.vue"),
];

type MobileNavPrefetchKey = Exclude<MobileNavKey, "todo">;

const mobileNavPrefetchers: Record<MobileNavPrefetchKey, () => Promise<unknown>> = {
  leads: () => import("../views/LeadView.vue"),
  customers: () => import("../views/CustomersView.vue"),
  billing: () => import("../views/BillingView.vue"),
  more: () => import("../views/mobile/MobileMoreView.vue"),
};

const mobileMoreEntryPrefetchers = {
  "receipt-reconciliation": () => import("../views/ReceiptReconciliationView.vue"),
  "common-library": () => import("../views/CommonLibraryView.vue"),
  "address-resources": () => import("../views/AddressResourceView.vue"),
} as const;

const mobileRoutePrefetchers = {
  "/m/todo": [
    () => import("../views/mobile/MobileTodoView.vue"),
  ],
  "/m/leads": [
    () => import("../views/LeadView.vue"),
    () => import("../views/LeadDetailView.vue"),
  ],
  "/m/customers": [
    () => import("../views/CustomersView.vue"),
    () => import("../views/CustomerDetailView.vue"),
  ],
  "/m/billing": [
    () => import("../views/BillingView.vue"),
    () => import("../views/ReceiptReconciliationView.vue"),
  ],
  "/m/more": [
    () => import("../views/mobile/MobileMoreView.vue"),
    () => import("../views/CommonLibraryView.vue"),
    () => import("../views/AddressResourceView.vue"),
  ],
  "/m/receipt-reconciliation": [
    () => import("../views/ReceiptReconciliationView.vue"),
  ],
  "/m/common-library": [
    () => import("../views/CommonLibraryView.vue"),
  ],
  "/m/address-resources": [
    () => import("../views/AddressResourceView.vue"),
  ],
} as const;

let mobileWorkspacePrefetchScheduled = false;
let mobileWorkspacePrefetchCompleted = false;
let mobileSecondaryPrefetchScheduled = false;
let mobileSecondaryPrefetchCompleted = false;
const mobileNavPrefetchedKeys = new Set<MobileNavPrefetchKey>();
const mobileMoreEntryPrefetchedKeys = new Set<keyof typeof mobileMoreEntryPrefetchers>();
const mobileRoutePrefetchedPaths = new Set<keyof typeof mobileRoutePrefetchers>();

function normalizePrefetchPath(path: string): string {
  const [pathname = "/"] = String(path || "/").split("?");
  if (!pathname) return "/";
  if (pathname.length > 1) {
    return pathname.replace(/\/+$/, "");
  }
  return pathname;
}

function runMobileWorkspacePrefetch() {
  mobileWorkspacePrefetchScheduled = false;
  if (mobileWorkspacePrefetchCompleted || !isHandsetViewport()) return;
  mobileWorkspacePrefetchCompleted = true;

  for (const load of mobileWorkspacePrefetchers) {
    void load().catch(() => {
      // Ignore background prefetch failures.
    });
  }
}

function runMobileSecondaryPrefetch() {
  mobileSecondaryPrefetchScheduled = false;
  if (mobileSecondaryPrefetchCompleted || !isHandsetViewport()) return;
  mobileSecondaryPrefetchCompleted = true;

  for (const load of mobileSecondaryPrefetchers) {
    void load().catch(() => {
      // Ignore background prefetch failures.
    });
  }
}

export function scheduleMobileWorkspacePrefetch() {
  if (
    typeof window === "undefined" ||
    mobileWorkspacePrefetchCompleted ||
    mobileWorkspacePrefetchScheduled ||
    !isHandsetViewport()
  ) {
    return;
  }

  mobileWorkspacePrefetchScheduled = true;
  window.setTimeout(runMobileWorkspacePrefetch, PREFETCH_DELAY_MS);
}

export function scheduleMobileTodoIdlePrefetch() {
  if (
    typeof window === "undefined" ||
    mobileSecondaryPrefetchCompleted ||
    mobileSecondaryPrefetchScheduled ||
    !isHandsetViewport()
  ) {
    return;
  }

  mobileSecondaryPrefetchScheduled = true;

  const idleWindow = window as IdleWindow;
  if (typeof idleWindow.requestIdleCallback === "function") {
    idleWindow.requestIdleCallback(() => {
      runMobileSecondaryPrefetch();
    }, { timeout: IDLE_PREFETCH_TIMEOUT_MS });
    return;
  }

  window.setTimeout(runMobileSecondaryPrefetch, SECONDARY_PREFETCH_FALLBACK_DELAY_MS);
}

export function prefetchMobileNavTarget(key: MobileNavKey) {
  if (typeof window === "undefined" || !isHandsetViewport() || key === "todo") return;

  const navKey = key as MobileNavPrefetchKey;
  const load = mobileNavPrefetchers[navKey];
  if (!load || mobileNavPrefetchedKeys.has(navKey)) return;

  mobileNavPrefetchedKeys.add(navKey);
  void load().catch(() => {
    mobileNavPrefetchedKeys.delete(navKey);
  });
}

export function prefetchMobileMoreEntry(key: string) {
  if (typeof window === "undefined" || !isHandsetViewport()) return;

  const load = mobileMoreEntryPrefetchers[key as keyof typeof mobileMoreEntryPrefetchers];
  if (!load) return;

  const entryKey = key as keyof typeof mobileMoreEntryPrefetchers;
  if (mobileMoreEntryPrefetchedKeys.has(entryKey)) return;

  mobileMoreEntryPrefetchedKeys.add(entryKey);
  void load().catch(() => {
    mobileMoreEntryPrefetchedKeys.delete(entryKey);
  });
}

export function prefetchMobileRoutePath(path: string): boolean {
  if (typeof window === "undefined" || !isHandsetViewport()) return false;

  const normalizedPath = normalizePrefetchPath(path) as keyof typeof mobileRoutePrefetchers;
  const loaders = mobileRoutePrefetchers[normalizedPath];
  if (!loaders || mobileRoutePrefetchedPaths.has(normalizedPath)) return false;

  mobileRoutePrefetchedPaths.add(normalizedPath);
  for (const load of loaders) {
    void load().catch(() => {
      mobileRoutePrefetchedPaths.delete(normalizedPath);
    });
  }

  return true;
}
