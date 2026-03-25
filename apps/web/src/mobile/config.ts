import type { UserInfo } from "../types";

export const HANDSET_BREAKPOINT = 768;
export const HANDSET_MEDIA_QUERY = `(max-width: ${HANDSET_BREAKPOINT}px)`;

export type MobileNavKey = "todo" | "leads" | "customers" | "billing" | "more";

export type MobileNavItem = {
  key: MobileNavKey;
  label: string;
  path: string;
};

export type MobileMoreEntry = {
  key: string;
  label: string;
  description: string;
  path: string;
  group: "finance" | "resources" | "management";
  visible?: (user: UserInfo | null) => boolean;
};

export type MobileMoreSection = {
  key: "finance" | "resources" | "management";
  label: string;
  description: string;
  entries: MobileMoreEntry[];
};

const primaryNavItems: MobileNavItem[] = [
  { key: "todo", label: "Todo", path: "/m/todo" },
  { key: "leads", label: "开发", path: "/m/leads" },
  { key: "customers", label: "客户", path: "/m/customers" },
  { key: "billing", label: "收费", path: "/m/billing" },
  { key: "more", label: "更多", path: "/m/more" },
];

const moreEntries: MobileMoreEntry[] = [
  {
    key: "receipt-reconciliation",
    label: "到账核对",
    description: "按账户核对收款。",
    path: "/m/receipt-reconciliation",
    group: "finance",
    visible: (user) =>
      user?.role === "OWNER" ||
      user?.role === "ADMIN" ||
      user?.role === "MANAGER" ||
      Boolean(user?.granted_read_modules.includes("BILLING")),
  },
  {
    key: "common-library",
    label: "常用资料",
    description: "查模板、资料和公开内容。",
    path: "/m/common-library",
    group: "resources",
  },
  {
    key: "address-resources",
    label: "挂靠地址",
    description: "查地址、联系人和备注。",
    path: "/m/address-resources",
    group: "resources",
  },
  {
    key: "costs",
    label: "成本与老板视图",
    description: "老板查看成本和视图数据。",
    path: "/m/costs",
    group: "finance",
    visible: (user) => user?.role === "OWNER",
  },
  {
    key: "admin-users",
    label: "管理员面板",
    description: "管理用户、角色和授权。",
    path: "/m/admin/users",
    group: "management",
    visible: (user) => user?.role === "OWNER" || user?.role === "ADMIN",
  },
];

const moreSectionMeta: Array<Omit<MobileMoreSection, "entries">> = [
  {
    key: "finance",
    label: "财务协作",
    description: "到账、收费和老板视图入口。",
  },
  {
    key: "resources",
    label: "资料与资源",
    description: "资料库和地址资源入口。",
  },
  {
    key: "management",
    label: "系统管理",
    description: "后台与授权入口。",
  },
];

export function isHandsetViewport(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia(HANDSET_MEDIA_QUERY).matches;
}

export function isMobileAppPath(path: string): boolean {
  return path === "/m" || path.startsWith("/m/");
}

export function getDefaultProtectedPath(): string {
  return isHandsetViewport() ? "/m/todo" : "/dashboard";
}

export function getMobilePrimaryNavItems(): MobileNavItem[] {
  return primaryNavItems;
}

export function getMobileMoreEntries(user: UserInfo | null): MobileMoreEntry[] {
  return moreEntries.filter((item) => (item.visible ? item.visible(user) : true));
}

export function getMobileMoreSections(user: UserInfo | null): MobileMoreSection[] {
  const visibleEntries = getMobileMoreEntries(user);
  return moreSectionMeta
    .map((section) => ({
      ...section,
      entries: visibleEntries.filter((item) => item.group === section.key),
    }))
    .filter((section) => section.entries.length > 0);
}

export function getRoleLabel(user: UserInfo | null): string {
  if (!user) return "-";
  if (user.role === "OWNER") return "老板";
  if (user.role === "ADMIN") return "管理员";
  if (user.role === "MANAGER") return "部门经理";
  return "会计";
}

type RouteMapping = {
  match: RegExp;
  build: (match: RegExpExecArray, search: string) => string;
};

const mobileMappings: RouteMapping[] = [
  {
    match: /^\/$/,
    build: (_match, search) => `/m/todo${search}`,
  },
  {
    match: /^\/dashboard$/,
    build: (_match, search) => `/m/todo${search}`,
  },
  {
    match: /^\/leads$/,
    build: (_match, search) => `/m/leads${search}`,
  },
  {
    match: /^\/leads\/(\d+)$/,
    build: (match, search) => `/m/leads/${match[1]}${search}`,
  },
  {
    match: /^\/customers$/,
    build: (_match, search) => `/m/customers${search}`,
  },
  {
    match: /^\/customers\/(\d+)$/,
    build: (match, search) => `/m/customers/${match[1]}${search}`,
  },
  {
    match: /^\/billing$/,
    build: (_match, search) => `/m/billing${search}`,
  },
  {
    match: /^\/receipt-reconciliation$/,
    build: (_match, search) => `/m/receipt-reconciliation${search}`,
  },
  {
    match: /^\/common-library$/,
    build: (_match, search) => `/m/common-library${search}`,
  },
  {
    match: /^\/address-resources$/,
    build: (_match, search) => `/m/address-resources${search}`,
  },
  {
    match: /^\/admin\/users$/,
    build: (_match, search) => `/m/admin/users${search}`,
  },
  {
    match: /^\/costs$/,
    build: (_match, search) => `/m/costs${search}`,
  },
];

export function mapPathToMobile(rawPath: string): string | null {
  if (!rawPath) return null;
  const url = new URL(rawPath, "http://local.codex");
  const pathname = url.pathname;
  const search = url.search;
  for (const item of mobileMappings) {
    const match = item.match.exec(pathname);
    if (match) {
      return item.build(match, search);
    }
  }
  return null;
}

export function mapPathForCurrentViewport(rawPath: string): string {
  if (!isHandsetViewport()) return rawPath;
  return mapPathToMobile(rawPath) ?? rawPath;
}

export function resolveMobileBackPath(rawPath: string | null | undefined, fallback = "/m/todo"): string {
  if (!rawPath) return fallback;
  return mapPathToMobile(rawPath) ?? rawPath;
}
