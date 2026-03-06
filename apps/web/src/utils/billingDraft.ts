import type { BillingCreatePayload } from "../types";
import { todayInBrowserTimeZone } from "./time";

export const paymentMethodOptions = [
  { value: "预收", label: "预收" },
  { value: "后收", label: "后收" },
] as const;

export const chargeCategoryOptions = [
  "注册",
  "代账",
  "代账并退税",
  "单独退税",
  "咨询",
  "课程",
  "海外注册",
  "其他",
] as const;

export const chargeModeOptions = [
  { value: "PERIODIC", label: "按期" },
  { value: "ONE_TIME", label: "按次" },
] as const;

const periodicAmountBasisOptions = [
  { value: "MONTHLY", label: "月费" },
  { value: "YEARLY", label: "年费" },
  { value: "PERIOD_TOTAL", label: "周期总价" },
] as const;

const oneTimeAmountBasisOptions = [{ value: "ONE_TIME", label: "单次费用" }] as const;

export const billingStatusOptions = [
  { value: "CLEARED", label: "清账" },
  { value: "PARTIAL", label: "部分收费" },
  { value: "FULL_ARREARS", label: "全欠" },
] as const;

export const billingCycleOptions = [
  "按月（每月收）",
  "按季（每3个月收）",
  "半年（每6个月收）",
  "全年（每12个月收）",
  "一次性（单次服务）",
  "自定义周期（见备注）",
] as const;

export const billingFieldHelp = {
  serial_no: "留空后系统会自动顺延编号，只有补录历史单据时才建议手动填写。",
  charge_category: "同一客户可同时存在多条收费项，例如代账、注册、咨询分别增行录入。",
  charge_mode: "按期用于持续服务合同；按次用于股权变更、咨询等一次性项目。",
  amount_basis:
    "金额口径用于解释费用单位。按次会固定为单次费用；按期会先按服务开始日期给出默认到期日期。",
  summary: "让会计和老板一眼看懂这条收费单在做什么，例如“2026年度代账服务”。",
  total_fee: "该收费项整个服务期应收的总金额。",
  monthly_fee: "用于统计月度盘子。按月费可直接填月费；按年费或周期总价可填折算月费。",
  collection_start_date: "服务实际开始日期。系统会据此自动推导内部开始月份。",
  due_month: "合同或服务结束日期。按期会先按服务开始日期和金额口径自动带出，仍可手动修改。",
  payment_method: "预收表示服务开始前先收费；后收表示服务完成或账期结束后再收费。",
  billing_cycle_text: "给老板/会计看的补充说明，不参与核心金额计算。",
  status: "通常由系统根据总费用和已收金额自动得出；只有补录历史单据时才需要手动改。",
  received_amount: "新增时通常填 0；如果开单时已经收到部分款，可以直接录入。",
  note: "记录合同约定、包含项目、优惠或终止说明等关键信息。",
  extra_note: "内部补充说明，不影响台账金额计算。",
} as const;

function parseDateText(dateText: string): Date | null {
  const token = (dateText || "").trim();
  const matched = token.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!matched) return null;
  const year = Number(matched[1]);
  const month = Number(matched[2]);
  const day = Number(matched[3]);
  const value = new Date(year, month - 1, day);
  if (
    Number.isNaN(value.getTime()) ||
    value.getFullYear() !== year ||
    value.getMonth() !== month - 1 ||
    value.getDate() !== day
  ) {
    return null;
  }
  return value;
}

function formatDateText(value: Date): string {
  const year = value.getFullYear();
  const month = `${value.getMonth() + 1}`.padStart(2, "0");
  const day = `${value.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function subtractDays(value: Date, days: number): Date {
  const next = new Date(value.getFullYear(), value.getMonth(), value.getDate());
  next.setDate(next.getDate() - days);
  return next;
}

function addMonthsClamped(value: Date, months: number): Date {
  const year = value.getFullYear();
  const month = value.getMonth();
  const day = value.getDate();
  const targetMonthIndex = year * 12 + month + months;
  const targetYear = Math.floor(targetMonthIndex / 12);
  const targetMonth = targetMonthIndex % 12;
  const lastDay = new Date(targetYear, targetMonth + 1, 0).getDate();
  return new Date(targetYear, targetMonth, Math.min(day, lastDay));
}

function addYearsClamped(value: Date, years: number): Date {
  const year = value.getFullYear() + years;
  const month = value.getMonth();
  const day = value.getDate();
  const lastDay = new Date(year, month + 1, 0).getDate();
  return new Date(year, month, Math.min(day, lastDay));
}

function lastDayOfMonthText(monthText: string): string {
  const token = (monthText || "").trim();
  if (token.length !== 7 || token[4] !== "-") return "";
  const year = Number(token.slice(0, 4));
  const month = Number(token.slice(5, 7));
  if (!Number.isFinite(year) || !Number.isFinite(month) || month < 1 || month > 12) return "";
  const lastDay = new Date(year, month, 0).getDate();
  return `${token}-${`${lastDay}`.padStart(2, "0")}`;
}

function monthFromDateText(dateText: string): string {
  const token = (dateText || "").trim();
  return token.length >= 7 ? token.slice(0, 7) : "";
}

function deriveDueDateFromDraft(draft: BillingCreatePayload): string {
  const serviceStart = parseDateText(draft.collection_start_date);
  if (!serviceStart) return "";

  if (draft.charge_mode === "ONE_TIME") {
    return formatDateText(serviceStart);
  }

  if (draft.amount_basis === "MONTHLY") {
    return formatDateText(subtractDays(addMonthsClamped(serviceStart, 1), 1));
  }
  return formatDateText(subtractDays(addYearsClamped(serviceStart, 1), 1));
}

export function getAmountBasisOptions(chargeMode: BillingCreatePayload["charge_mode"]) {
  return chargeMode === "ONE_TIME" ? oneTimeAmountBasisOptions : periodicAmountBasisOptions;
}

export function getMonthlyFeeLabel(draft: BillingCreatePayload): string {
  if (draft.amount_basis === "MONTHLY") return "月费";
  return "折算月费";
}

export function shiftMonth(monthText: string, delta: number): string {
  const token = (monthText || "").trim();
  if (token.length !== 7 || token[4] !== "-") return "";
  const year = Number(token.slice(0, 4));
  const month = Number(token.slice(5, 7));
  if (!Number.isFinite(year) || !Number.isFinite(month) || month < 1 || month > 12) return "";
  const monthIndex = year * 12 + (month - 1) + delta;
  const targetYear = Math.floor(monthIndex / 12);
  const targetMonth = (monthIndex % 12) + 1;
  return `${targetYear.toString().padStart(4, "0")}-${targetMonth.toString().padStart(2, "0")}`;
}

export function shiftDateText(dateText: string, years: number): string {
  const token = (dateText || "").trim();
  if (!token) return "";
  const source = parseDateText(token);
  if (!source) return token;
  const next = addYearsClamped(source, years);
  return formatDateText(next);
}

export function createEmptyBillingDraft(customerId: number | null = null): BillingCreatePayload {
  const draft: BillingCreatePayload = {
    serial_no: null,
    customer_id: customerId,
    charge_category: "代账",
    charge_mode: "PERIODIC",
    amount_basis: "MONTHLY",
    summary: "",
    total_fee: 0,
    monthly_fee: 0,
    billing_cycle_text: "按月（每月收）",
    period_start_month: "",
    period_end_month: "",
    collection_start_date: "",
    due_month: "",
    payment_method: "预收",
    status: "PARTIAL",
    received_amount: 0,
    note: "",
    extra_note: "",
    color_tag: "",
  };
  syncBillingDerivedDates(draft);
  return draft;
}

export function cloneBillingDraft(source: BillingCreatePayload): BillingCreatePayload {
  return {
    ...source,
  };
}

function applyBillingModeDefaults(draft: BillingCreatePayload) {
  if (draft.charge_mode === "ONE_TIME") {
    draft.amount_basis = "ONE_TIME";
    draft.period_start_month = "";
    draft.period_end_month = "";
    if (!draft.billing_cycle_text || draft.billing_cycle_text === "按月（每月收）") {
      draft.billing_cycle_text = "一次性（单次服务）";
    }
    const baseDate = draft.collection_start_date || draft.due_month || todayInBrowserTimeZone();
    draft.collection_start_date = baseDate;
    draft.due_month = baseDate;
    return;
  }

  if (draft.amount_basis === "ONE_TIME") {
    draft.amount_basis = "MONTHLY";
  }
  if (!draft.billing_cycle_text || draft.billing_cycle_text === "一次性（单次服务）") {
    draft.billing_cycle_text = "按月（每月收）";
  }
}

export function syncBillingDerivedDates(
  draft: BillingCreatePayload,
  options: { recalculateDue?: boolean } = {},
) {
  applyBillingModeDefaults(draft);

  if (draft.collection_start_date) {
    draft.period_start_month = monthFromDateText(draft.collection_start_date);
  }

  if (draft.charge_mode === "ONE_TIME") {
    if (options.recalculateDue || !draft.due_month) {
      draft.due_month = draft.collection_start_date || todayInBrowserTimeZone();
    }
    draft.period_start_month = "";
    draft.period_end_month = "";
    return;
  }

  if (!draft.collection_start_date && draft.period_start_month) {
    draft.collection_start_date = `${draft.period_start_month}-01`;
  }

  if (draft.collection_start_date && (options.recalculateDue || !draft.due_month)) {
    draft.due_month = deriveDueDateFromDraft(draft);
  }

  if (draft.due_month) {
    draft.period_end_month = monthFromDateText(draft.due_month);
  } else if (draft.period_end_month) {
    draft.due_month = lastDayOfMonthText(draft.period_end_month);
  }
}

export function validateBillingDraft(draft: BillingCreatePayload, index: number): string | null {
  const rowLabel = `第 ${index + 1} 行`;
  if (!draft.customer_id) {
    return `${rowLabel}缺少客户信息`;
  }
  if (draft.total_fee <= 0) {
    return `${rowLabel}总费用必须大于 0`;
  }
  if (!draft.collection_start_date) {
    return `${rowLabel}请填写服务开始日期`;
  }
  if (!draft.due_month) {
    return `${rowLabel}请填写到期日期`;
  }
  const serviceStart = parseDateText(draft.collection_start_date);
  const dueDate = parseDateText(draft.due_month);
  if (!serviceStart) {
    return `${rowLabel}服务开始日期格式不正确`;
  }
  if (!dueDate) {
    return `${rowLabel}到期日期格式不正确`;
  }
  if (dueDate < serviceStart) {
    return `${rowLabel}到期日期不能早于服务开始日期`;
  }
  return null;
}

function prepareBillingDraftForSubmit(draft: BillingCreatePayload): BillingCreatePayload {
  const next = cloneBillingDraft(draft);
  syncBillingDerivedDates(next);
  return next;
}

export function prepareBillingDraftsForSubmit(drafts: BillingCreatePayload[]): BillingCreatePayload[] {
  return drafts.map((draft) => prepareBillingDraftForSubmit(draft));
}
