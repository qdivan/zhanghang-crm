import type {
  BillingAssignmentKind,
  BillingAssignmentRole,
  BillingExecutionProgressType,
  BillingPaymentStrategy,
} from "../../types";

export const assignmentKindOptions: Array<{ value: BillingAssignmentKind; label: string }> = [
  { value: "PRIMARY", label: "当前负责人" },
  { value: "CC", label: "抄送" },
];

export const assignmentRoleOptions: Array<{ value: BillingAssignmentRole; label: string }> = [
  { value: "REGISTRATION", label: "注册办理" },
  { value: "DELIVERY", label: "交付执行" },
  { value: "OTHER", label: "其他支持" },
];

export function assignmentKindLabel(value: BillingAssignmentKind | string): string {
  if (value === "PRIMARY") return "当前负责人";
  return "抄送";
}

export const progressTypeOptions: Array<{ value: BillingExecutionProgressType; label: string }> = [
  { value: "UPDATE", label: "进展更新" },
  { value: "MILESTONE", label: "里程碑" },
  { value: "BLOCKER", label: "阻塞问题" },
  { value: "DONE", label: "执行完成" },
];

export const paymentStrategyOptions: Array<{ value: BillingPaymentStrategy; label: string }> = [
  { value: "DUE_DATE_ASC", label: "到期优先（默认）" },
  { value: "SERIAL_ASC", label: "序号优先" },
  { value: "AMOUNT_DESC", label: "大额优先" },
];

export const paymentMethodHelpLines = [
  "预收：服务开始前先收费",
  "后收：到期日/账期结束后再收费",
];

export const receiptAccountOptions = [
  { value: "一帆光大", label: "一帆光大" },
  { value: "一帆青岛", label: "一帆青岛" },
  { value: "微信", label: "微信" },
  { value: "支付宝", label: "支付宝" },
  { value: "聚能", label: "聚能" },
  { value: "未指定", label: "未指定" },
];

export const receiptAccountHelpLines = [
  "收款时请登记实际入账账户，方便老板、部门经理和管理员按账户核对流水。",
  "同一客户整笔收款分摊到多个收费项时，仍只记一个入账账户。",
];

export const billingMonthHelpLines = [
  "按应收期间筛选，例如选择 2025-03 会筛出该月应收范围内的收费项。",
  "按次项目会按服务日期/到期日期落到对应月份。",
];

export const billingStatusHelpLines = [
  "清账：已收齐，未收金额为 0",
  "部分收费：已收部分，仍有未收",
  "全欠：尚未收款",
];

export const billingTableHelpLines = [
  "按期项目先录开始月份，系统默认顺延 12 个月，并自动换算月初/月末日期。",
  "按次项目再录服务日期和到期日期，金额口径固定为单次费用。",
  "如果合同不是整年，可以手动调整结束月份。",
];

export function normalizePaymentMethod(value: string): "预收" | "后收" {
  return value === "预收" ? "预收" : "后收";
}

export function statusLabel(status: string): string {
  if (status === "CLEARED") return "清账";
  if (status === "FULL_ARREARS") return "全欠";
  return "部分收费";
}

export function statusTagType(status: string): string {
  if (status === "CLEARED") return "success";
  if (status === "FULL_ARREARS") return "danger";
  return "warning";
}

export function activityTypeLabel(type: string): string {
  return type === "PAYMENT" ? "收款" : "催收";
}

function readActivityTypeToken(value: unknown): string {
  if (typeof value === "string") {
    return value.trim();
  }
  if (value && typeof value === "object") {
    const maybeValue = (value as Record<string, unknown>).value;
    if (typeof maybeValue === "string") {
      return maybeValue.trim();
    }
    const maybeLabel = (value as Record<string, unknown>).label;
    if (typeof maybeLabel === "string") {
      return maybeLabel.trim();
    }
    const maybeType = (value as Record<string, unknown>).activity_type;
    if (typeof maybeType === "string") {
      return maybeType.trim();
    }
  }
  return "";
}

export function normalizeActivityType(value: unknown): "REMINDER" | "PAYMENT" {
  const token = readActivityTypeToken(value);
  const upper = token.toUpperCase();
  if (upper === "PAYMENT" || token.includes("收款")) {
    return "PAYMENT";
  }
  return "REMINDER";
}

export function isPaymentActivityType(value: unknown): boolean {
  const token = readActivityTypeToken(value);
  const upper = token.toUpperCase();
  if (!token) return false;
  if (upper === "REMINDER" || token.includes("催收")) return false;
  if (upper === "PAYMENT" || token.includes("收款")) return true;
  return true;
}

export function assignmentRoleLabel(role: string): string {
  if (role === "REGISTRATION") return "注册办理";
  if (role === "DELIVERY") return "交付执行";
  return "其他支持";
}

export function progressTypeLabel(type: string): string {
  if (type === "MILESTONE") return "里程碑";
  if (type === "BLOCKER") return "阻塞问题";
  if (type === "DONE") return "执行完成";
  return "进展更新";
}

export function progressTypeTagType(type: string): string {
  if (type === "MILESTONE") return "success";
  if (type === "BLOCKER") return "danger";
  if (type === "DONE") return "primary";
  return "info";
}

export function ledgerSourceLabel(sourceType: string): string {
  return sourceType === "PAYMENT" ? "实收" : "应收";
}

export function getMonthDateRange(monthText: string): [string, string] | null {
  const token = (monthText || "").trim();
  if (token.length !== 7 || token[4] !== "-") return null;
  const year = Number(token.slice(0, 4));
  const month = Number(token.slice(5, 7));
  if (!Number.isFinite(year) || !Number.isFinite(month) || month < 1 || month > 12) return null;
  const start = `${year.toString().padStart(4, "0")}-${month.toString().padStart(2, "0")}-01`;
  const endDay = new Date(year, month, 0).getDate();
  const end = `${year.toString().padStart(4, "0")}-${month.toString().padStart(2, "0")}-${endDay.toString().padStart(2, "0")}`;
  return [start, end];
}
