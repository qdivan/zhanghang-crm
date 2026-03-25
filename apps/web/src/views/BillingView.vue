<script setup lang="ts">
import { Filter } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, nextTick, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { apiClient } from "../api/client";
import MobileActionSheet from "../components/mobile/MobileActionSheet.vue";
import MobileFilterSheet from "../components/mobile/MobileFilterSheet.vue";
import BillingActivityDrawer from "../components/billing/BillingActivityDrawer.vue";
import BillingAssignmentDialog from "../components/billing/BillingAssignmentDialog.vue";
import BillingCreateDialog from "../components/billing/BillingCreateDialog.vue";
import BillingExecutionDrawer from "../components/billing/BillingExecutionDrawer.vue";
import BillingFilterCard from "../components/billing/BillingFilterCard.vue";
import BillingLedgerDialog from "../components/billing/BillingLedgerDialog.vue";
import BillingLedgerPanel from "../components/billing/BillingLedgerPanel.vue";
import BillingRecordsCard from "../components/billing/BillingRecordsCard.vue";
import BillingRenewDialog from "../components/billing/BillingRenewDialog.vue";
import BillingSplitPaymentDialog from "../components/billing/BillingSplitPaymentDialog.vue";
import BillingSummaryPanel from "../components/billing/BillingSummaryPanel.vue";
import BillingTerminateDialog from "../components/billing/BillingTerminateDialog.vue";
import { useMobileFilterMemory } from "../composables/useMobileFilterMemory";
import { useResponsive } from "../composables/useResponsive";
import { isMobileAppPath } from "../mobile/config";
import { useAuthStore } from "../stores/auth";
import type {
  BillingActivity,
  BillingCreatePayload,
  BillingAssignmentItem,
  BillingExecutionLogItem,
  BillingLedgerData,
  BillingPaymentSuggestion,
  BillingRecord,
  CustomerListItem,
} from "../types";
import {
  createEmptyBillingDraft,
  prepareBillingDraftsForSubmit,
  shiftDateText,
  shiftMonth,
  validateBillingDraft,
} from "../utils/billingDraft";
import { normalizeDateText } from "../utils/dateInput";
import { todayInBrowserTimeZone } from "../utils/time";
import {
  type BillingSplitAllocationRow,
  type BillingActivityForm,
  createBillingActivityForm,
  createBillingAssignmentForm,
  createBillingExecutionForm,
  createBillingFilters,
  createBillingSplitPaymentForm,
  createBillingTerminateForm,
  type BillingAssignmentForm,
  type BillingExecutionForm,
  type BillingSplitPaymentForm,
  type BillingTerminateForm,
} from "./billing/forms";
import {
  getMonthDateRange,
  isPaymentActivityType,
  normalizeActivityType,
  normalizePaymentMethod,
  receiptAccountOptions,
  statusLabel,
} from "./billing/viewMeta";

type UserLite = {
  id: number;
  username: string;
  role: string;
};

type BillingQuickView = "ALL" | "OVERDUE" | "DUE_SOON" | "OPEN" | "CLEARED";

type BillingRowInsights = {
  visibleOutstandingTotal: number;
  dueSoonCount: number;
  overdueCount: number;
  openBillingCount: number;
  clearedBillingCount: number;
  overdueRows: BillingRecord[];
  dueSoonRows: BillingRecord[];
  openRows: BillingRecord[];
  clearedRows: BillingRecord[];
};

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const { isMobile } = useResponsive();
const loading = ref(false);
const summaryLoading = ref(false);
const billingListHydrated = ref(false);
const billingSummaryHydrated = ref(false);
const rows = ref<BillingRecord[]>([]);
const customers = ref<CustomerListItem[]>([]);
const summary = ref({
  total_records: 0,
  total_fee: 0,
  total_monthly_fee: 0,
  payment_method_distribution: [] as Array<{ payment_method: string; count: number }>,
  status_distribution: [] as Array<{ status: string; count: number }>,
  receipt_account_distribution: [] as Array<{ receipt_account: string; payment_count: number; total_amount: number }>,
});

const billingQuickView = ref<BillingQuickView>("ALL");
const filters = reactive(createBillingFilters());
const billingMobileFilterMemory = useMobileFilterMemory("crm.mobile_filters.billing", {
  ...createBillingFilters(),
  quick_view: "ALL",
});
const customerFilterOptions = computed(() => customers.value);

const showCreateDialog = ref(false);
const createCustomerId = ref<number | null>(null);
const createRows = ref<BillingCreatePayload[]>([createEmptyBillingDraft(null)]);
const showRenewDialog = ref(false);
const renewing = ref(false);
const renewTargetRecord = ref<BillingRecord | null>(null);
const renewRows = ref<BillingCreatePayload[]>([createEmptyBillingDraft(null)]);

const paymentMethodDistributionNormalized = computed(() => {
  const grouped = new Map<"预收" | "后收", number>();
  for (const item of summary.value.payment_method_distribution) {
    const key = normalizePaymentMethod(item.payment_method);
    grouped.set(key, (grouped.get(key) || 0) + item.count);
  }
  return Array.from(grouped.entries()).map(([payment_method, count]) => ({ payment_method, count }));
});

const showActivityDrawer = ref(false);
const activityLoading = ref(false);
const activityRows = ref<BillingActivity[]>([]);
const selectedRecord = ref<BillingRecord | null>(null);
const activityForm = reactive<BillingActivityForm>(createBillingActivityForm(todayInBrowserTimeZone()));
const canManageGrant = computed(() => auth.user?.role === "OWNER" || auth.user?.role === "ADMIN");
const canManageAssignment = computed(
  () => auth.user?.role === "OWNER" || auth.user?.role === "ADMIN" || auth.user?.role === "MANAGER",
);
const showAssignmentDialog = ref(false);
const assignmentLoading = ref(false);
const assignmentSubmitting = ref(false);
const assignmentRows = ref<BillingAssignmentItem[]>([]);
const assignmentTargetRecord = ref<BillingRecord | null>(null);
const assignableUsers = ref<UserLite[]>([]);
const assignmentForm = reactive<BillingAssignmentForm>(createBillingAssignmentForm());
const showExecutionDrawer = ref(false);
const executionLoading = ref(false);
const executionSubmitting = ref(false);
const executionRows = ref<BillingExecutionLogItem[]>([]);
const executionTargetRecord = ref<BillingRecord | null>(null);
const executionForm = reactive<BillingExecutionForm>(createBillingExecutionForm(todayInBrowserTimeZone()));
const showSplitPaymentDialog = ref(false);
const splitSuggestionLoading = ref(false);
const splitSubmitting = ref(false);
const splitTargetRecord = ref<BillingRecord | null>(null);
const splitCustomerRecordCount = ref(0);
const splitAllocations = ref<BillingSplitAllocationRow[]>([]);
const splitForm = reactive<BillingSplitPaymentForm>(createBillingSplitPaymentForm(todayInBrowserTimeZone()));
const canManageBillingLifecycle = computed(
  () => auth.user?.role === "OWNER" || auth.user?.role === "ADMIN" || auth.user?.role === "MANAGER",
);
const showTerminateDialog = ref(false);
const terminating = ref(false);
const terminateTargetRecord = ref<BillingRecord | null>(null);
const terminateForm = reactive<BillingTerminateForm>(createBillingTerminateForm(todayInBrowserTimeZone()));
const showLedgerDialog = ref(false);
const ledgerLoading = ref(false);
const ledgerTargetRecord = ref<BillingRecord | null>(null);
const ledgerDateRange = ref<[string, string] | null>(null);
const ledgerData = ref<BillingLedgerData | null>(null);
const ledgerPanelAnchor = ref<HTMLElement | null>(null);
const ledgerCache = new Map<string, BillingLedgerData>();
const canViewReceiptLedger = computed(
  () =>
    auth.user?.role === "OWNER" ||
    auth.user?.role === "ADMIN" ||
    auth.user?.role === "MANAGER" ||
    Boolean(auth.user?.granted_read_modules.includes("BILLING")),
);
const ledgerHasDateFilter = computed(() => {
  return Boolean(ledgerDateRange.value?.[0] || ledgerDateRange.value?.[1]);
});
const routeActionHandling = ref(false);
const billingRouteQueueHandling = ref(false);
const showMobileFilters = ref(false);
const expandedBillingId = ref<number | null>(null);
const showBillingRowActionSheet = ref(false);
const selectedBillingActionRow = ref<BillingRecord | null>(null);
const isMobileWorkflow = computed(() => isMobileAppPath(route.path));

const splitAllocatedTotal = computed(() => {
  return splitAllocations.value.reduce((sum, item) => sum + Number(item.allocated_amount || 0), 0);
});

const splitRemainingAmount = computed(() => {
  return Number((splitForm.amount - splitAllocatedTotal.value).toFixed(2));
});

function getDaysUntilDue(dateText: string): number | null {
  const raw = (dateText || "").trim();
  if (!raw) return null;
  const due = new Date(`${raw}T00:00:00`);
  if (Number.isNaN(due.getTime())) return null;
  const today = new Date(`${todayInBrowserTimeZone()}T00:00:00`);
  return Math.round((due.getTime() - today.getTime()) / 86400000);
}

const billingRowInsights = computed<BillingRowInsights>(() => {
  let visibleOutstandingTotal = 0;
  let dueSoonCount = 0;
  let overdueCount = 0;
  let openBillingCount = 0;
  let clearedBillingCount = 0;
  const overdueRows: BillingRecord[] = [];
  const dueSoonRows: BillingRecord[] = [];
  const openRows: BillingRecord[] = [];
  const clearedRows: BillingRecord[] = [];

  for (const row of rows.value) {
    const outstanding = Number(row.outstanding_amount || 0);
    const isOpen = outstanding > 0;
    const isCleared = row.status === "CLEARED" || !isOpen;

    if (isOpen) {
      visibleOutstandingTotal += outstanding;
      openBillingCount += 1;
      openRows.push(row);

      const days = getDaysUntilDue(row.due_month || "");
      if (days !== null && days < 0) {
        overdueCount += 1;
        overdueRows.push(row);
      } else if (days !== null && days <= 7) {
        dueSoonCount += 1;
        dueSoonRows.push(row);
      }
    }

    if (isCleared) {
      clearedBillingCount += 1;
      clearedRows.push(row);
    }
  }

  return {
    visibleOutstandingTotal,
    dueSoonCount,
    overdueCount,
    openBillingCount,
    clearedBillingCount,
    overdueRows,
    dueSoonRows,
    openRows,
    clearedRows,
  };
});

const visibleOutstandingTotal = computed(() => billingRowInsights.value.visibleOutstandingTotal);
const dueSoonCount = computed(() => billingRowInsights.value.dueSoonCount);
const overdueCount = computed(() => billingRowInsights.value.overdueCount);
const openBillingCount = computed(() => billingRowInsights.value.openBillingCount);
const clearedBillingCount = computed(() => billingRowInsights.value.clearedBillingCount);

function formatAmount(value: number): string {
  const amount = Number(value || 0);
  return amount.toLocaleString("zh-CN", {
    minimumFractionDigits: Number.isInteger(amount) ? 0 : 2,
    maximumFractionDigits: 2,
  });
}

const mobileFocusSummary = computed(() => {
  if (overdueCount.value > 0) {
    return {
      title: "先处理逾期收费",
      detail: `${overdueCount.value} 条已逾期，优先催收和登记收款。`,
      tone: "danger",
    };
  }
  if (dueSoonCount.value > 0) {
    return {
      title: "近期待收需要跟进",
      detail: `${dueSoonCount.value} 条 7 天内到期，建议先联系客户。`,
      tone: "warning",
    };
  }
  if (visibleOutstandingTotal.value > 0) {
    return {
      title: "仍有未收款待推进",
      detail: `当前未收 ${formatAmount(visibleOutstandingTotal.value)}，继续保持跟进节奏。`,
      tone: "accent",
    };
  }
  return {
    title: "当前收费状态稳定",
    detail: "没有逾期或近期待收，继续维护台账与到账核对。",
    tone: "quiet",
  };
});

const mobileSummaryCards = computed(() => [
  { label: "未收合计", value: formatAmount(visibleOutstandingTotal.value), accent: true },
  { label: "7天内", value: String(dueSoonCount.value), warning: dueSoonCount.value > 0 },
  { label: "逾期", value: String(overdueCount.value), danger: overdueCount.value > 0 },
]);

const mobileHeadlineStats = computed(() => [
  `收费单 ${rows.value.length}`,
  `待处理 ${openBillingCount.value}`,
  `已清 ${clearedBillingCount.value}`,
]);

const billingFilterChips = computed(() => {
  const selectedCustomer = customers.value.find((item) => item.id === filters.customer_id)?.name;
  return [
    filters.keyword ? { key: "keyword", label: `关键词：${filters.keyword}` } : null,
    selectedCustomer ? { key: "customer_id", label: `客户：${selectedCustomer}` } : null,
    filters.billing_month ? { key: "billing_month", label: `月份：${filters.billing_month}` } : null,
    filters.receipt_account ? { key: "receipt_account", label: `账户：${filters.receipt_account}` } : null,
    filters.contact_name ? { key: "contact_name", label: `联系人：${filters.contact_name}` } : null,
    filters.payment_method ? { key: "payment_method", label: `收款方式：${filters.payment_method}` } : null,
    filters.status ? { key: "status", label: `状态：${statusLabel(filters.status)}` } : null,
  ].filter(Boolean) as Array<{
    key: "keyword" | "customer_id" | "billing_month" | "receipt_account" | "contact_name" | "payment_method" | "status";
    label: string;
  }>;
});
const activeFilterChips = computed(() => billingFilterChips.value.map((item) => item.label));
const showBillingListInitialSkeleton = computed(() => !billingListHydrated.value);
const showBillingSummarySkeleton = computed(() => !billingSummaryHydrated.value);

function currentBillingFilterSnapshot() {
  return {
    keyword: filters.keyword,
    customer_id: filters.customer_id,
    billing_month: filters.billing_month,
    receipt_account: filters.receipt_account,
    contact_name: filters.contact_name,
    payment_method: filters.payment_method,
    status: filters.status,
    quick_view: billingQuickView.value,
  };
}

function updateCreateRows(nextRows: BillingCreatePayload[]) {
  createRows.value = nextRows;
}

function updateRenewRows(nextRows: BillingCreatePayload[]) {
  renewRows.value = nextRows;
}

watch(createCustomerId, (customerId) => {
  createRows.value = createRows.value.map((item) => ({
    ...item,
    customer_id: customerId,
  }));
});

function canWriteBillingRecord(record: BillingRecord): boolean {
  if (auth.user?.role !== "ACCOUNTANT") return true;
  return record.accountant_username === auth.user.username;
}

function matchesBillingMonth(record: BillingRecord, targetMonth: string): boolean {
  const normalizedMonth = (targetMonth || "").trim();
  if (!normalizedMonth) return true;

  if (record.charge_mode === "ONE_TIME") {
    const serviceMonth = (record.collection_start_date || "").trim().slice(0, 7);
    const dueMonth = (record.due_month || "").trim().slice(0, 7);
    return serviceMonth === normalizedMonth || dueMonth === normalizedMonth;
  }

  const startMonth =
    (record.period_start_month || "").trim() ||
    (record.collection_start_date || "").trim().slice(0, 7) ||
    (((record.due_month || "").trim().slice(0, 7) && shiftMonth((record.due_month || "").trim().slice(0, 7), -11)) || "");
  const endMonth =
    (record.period_end_month || "").trim() ||
    (record.due_month || "").trim().slice(0, 7) ||
    (((record.collection_start_date || "").trim().slice(0, 7) &&
      shiftMonth((record.collection_start_date || "").trim().slice(0, 7), 11)) ||
      "");

  if (startMonth && endMonth) {
    return startMonth <= normalizedMonth && normalizedMonth <= endMonth;
  }
  if (startMonth) return startMonth === normalizedMonth;
  if (endMonth) return endMonth === normalizedMonth;
  return false;
}

function getDuePriority(record: BillingRecord): [number, string, number] {
  const outstanding = Number(record.outstanding_amount || 0);
  if (outstanding <= 0) {
    return [3, record.due_month || "9999-99-99", record.serial_no || record.id];
  }
  const due = (record.due_month || "").trim() || "9999-99-99";
  const dueDate = new Date(`${due}T00:00:00`);
  if (Number.isNaN(dueDate.getTime())) {
    return [2, due, record.serial_no || record.id];
  }
  const today = new Date(`${todayInBrowserTimeZone()}T00:00:00`);
  const diffDays = Math.round((dueDate.getTime() - today.getTime()) / 86400000);
  if (diffDays < 0) return [0, due, record.serial_no || record.id];
  if (diffDays <= 7) return [1, due, record.serial_no || record.id];
  return [2, due, record.serial_no || record.id];
}

async function fetchRecords() {
  loading.value = true;
  ledgerCache.clear();
  try {
    const resp = await apiClient.get<BillingRecord[]>("/billing-records", {
      params: {
        keyword: filters.keyword || undefined,
        customer_id: filters.customer_id || undefined,
        receipt_account: filters.receipt_account || undefined,
        contact_name: filters.contact_name || undefined,
      },
    });
    let filteredRows = resp.data;
    if (filters.billing_month) {
      filteredRows = filteredRows.filter((item) => matchesBillingMonth(item, filters.billing_month));
    }
    if (filters.payment_method) {
      filteredRows = filteredRows.filter((item) => normalizePaymentMethod(item.payment_method) === filters.payment_method);
    }
    if (filters.status) {
      filteredRows = filteredRows.filter((item) => item.status === filters.status);
    }
    rows.value = filteredRows
      .map((item) => ({
        item,
        priority: getDuePriority(item),
      }))
      .sort((left, right) => {
        const leftPriority = left.priority;
        const rightPriority = right.priority;
        if (leftPriority[0] !== rightPriority[0]) return leftPriority[0] - rightPriority[0];
        if (leftPriority[1] !== rightPriority[1]) return leftPriority[1].localeCompare(rightPriority[1]);
        return leftPriority[2] - rightPriority[2];
      })
      .map(({ item }) => item);
    if (!isMobile.value) {
      void prefetchLedgerRows(rows.value);
    }
  } catch (error) {
    ElMessage.error("获取收费记录失败");
  } finally {
    loading.value = false;
    billingListHydrated.value = true;
  }
}

async function fetchSummary() {
  summaryLoading.value = true;
  try {
    const resp = await apiClient.get("/billing-records/summary", {
      params: {
        keyword: filters.keyword || undefined,
        customer_id: filters.customer_id || undefined,
        receipt_account: filters.receipt_account || undefined,
        billing_month: filters.billing_month || undefined,
        contact_name: filters.contact_name || undefined,
        payment_method: filters.payment_method || undefined,
        status: filters.status || undefined,
      },
    });
    summary.value = resp.data;
  } catch (error) {
    ElMessage.error("获取收费统计失败");
  } finally {
    summaryLoading.value = false;
    billingSummaryHydrated.value = true;
  }
}

async function runBillingQuery() {
  if (isMobileWorkflow.value) {
    billingMobileFilterMemory.saveState(currentBillingFilterSnapshot());
  }
  await Promise.all([fetchRecords(), fetchSummary()]);
}

const billingQuickFilters = computed(() => [
  { key: "ALL" as BillingQuickView, label: "全部", count: rows.value.length },
  { key: "OVERDUE" as BillingQuickView, label: "逾期", count: overdueCount.value },
  { key: "DUE_SOON" as BillingQuickView, label: "7天内", count: dueSoonCount.value },
  { key: "OPEN" as BillingQuickView, label: "未收", count: openBillingCount.value },
  { key: "CLEARED" as BillingQuickView, label: "已清", count: clearedBillingCount.value },
]);

const billingVisibleRows = computed(() => {
  if (billingQuickView.value === "OVERDUE") {
    return billingRowInsights.value.overdueRows;
  }
  if (billingQuickView.value === "DUE_SOON") {
    return billingRowInsights.value.dueSoonRows;
  }
  if (billingQuickView.value === "OPEN") {
    return billingRowInsights.value.openRows;
  }
  if (billingQuickView.value === "CLEARED") {
    return billingRowInsights.value.clearedRows;
  }
  return rows.value;
});

const billingActivityQueueRows = computed(() =>
  billingVisibleRows.value.filter((row) => Number(row.outstanding_amount || 0) > 0 && canWriteBillingRecord(row)),
);

const billingActivityQueueLabel = computed(() => {
  const currentId = selectedRecord.value?.id ?? null;
  if (!currentId) return "";
  const currentIndex = billingActivityQueueRows.value.findIndex((item) => item.id === currentId);
  if (currentIndex < 0) return "";
  return `${currentIndex + 1} / ${billingActivityQueueRows.value.length}`;
});

const hasNextBillingActivityRecord = computed(() => {
  const currentId = selectedRecord.value?.id ?? null;
  if (!currentId) return false;
  const currentIndex = billingActivityQueueRows.value.findIndex((item) => item.id === currentId);
  return currentIndex >= 0 && currentIndex < billingActivityQueueRows.value.length - 1;
});

const billingListTitle = computed(() => {
  if (billingQuickView.value === "OVERDUE") return "逾期收费";
  if (billingQuickView.value === "DUE_SOON") return "近期待收";
  if (billingQuickView.value === "OPEN") return "未收收费";
  if (billingQuickView.value === "CLEARED") return "已清收费";
  return activeFilterChips.value.length ? "筛选结果" : "当前收费单";
});
const billingRowActionItems = computed(() => {
  const row = selectedBillingActionRow.value;
  if (!row) return [];
  return [
    { key: "ledger", label: "往来账", description: "查看当前客户的明细往来账。" },
    { key: "execution", label: "执行进度", description: "进入执行进度和交付过程。" },
    {
      key: "split",
      label: "分摊收款",
      description: canWriteBillingRecord(row) ? "按规则把一笔收款分摊到多条收费单。" : "当前账号没有这条收费单的写权限。",
      disabled: !canWriteBillingRecord(row),
    },
    canManageAssignment.value
      ? { key: "assignment", label: "分派执行", description: "把这条收费单分给执行人员处理。" }
      : null,
    canManageBillingLifecycle.value
      ? { key: "renew", label: "确认续费", description: "基于当前收费单快速生成续费单。" }
      : null,
    canManageBillingLifecycle.value
      ? { key: "terminate", label: "提前终止", description: "按提前结束情况冲减费用。", danger: true }
      : null,
  ].filter(Boolean) as Array<{ key: string; label: string; description: string; disabled?: boolean; danger?: boolean }>;
});

async function fetchCustomers() {
  try {
    const resp = await apiClient.get<CustomerListItem[]>("/customers");
    customers.value = [...resp.data].sort((left, right) => left.name.localeCompare(right.name, "zh-CN"));
  } catch (error) {
    ElMessage.error("获取客户列表失败");
  }
}

async function fetchAssignableUsers() {
  if (!canManageAssignment.value) return;
  if (assignableUsers.value.length) return;
  try {
    const resp = await apiClient.get<UserLite[]>("/users");
    assignableUsers.value = resp.data.filter((item) => item.role !== "OWNER");
  } catch (error) {
    ElMessage.error("获取可分派人员失败");
  }
}

async function createRecord() {
  if (!createCustomerId.value) {
    ElMessage.warning("请先选择客户");
    return;
  }
  const validationError = createRows.value
    .map((item, index) => validateBillingDraft(item, index))
    .find((item) => item);
  if (validationError) {
    ElMessage.warning(validationError);
    return;
  }
  try {
    const payload = prepareBillingDraftsForSubmit(createRows.value);
    const resp = await apiClient.post<BillingRecord[]>("/billing-records/batch", { records: payload });
    ElMessage.success(`已创建 ${resp.data.length} 条收费记录`);
    showCreateDialog.value = false;
    resetCreateRows();
    await fetchRecords();
    await fetchSummary();
  } catch (error) {
    ElMessage.error("创建失败（需老板/管理员/部门经理账号）");
  }
}

function resetCreateRows(customerId: number | null = null) {
  createCustomerId.value = customerId;
  createRows.value = [createEmptyBillingDraft(customerId)];
}

function openCreateDialog() {
  resetCreateRows();
  showCreateDialog.value = true;
}

function buildRenewDraft(record: BillingRecord): BillingCreatePayload {
  return {
    serial_no: null,
    customer_id: record.customer_id,
    charge_category: record.charge_category,
    charge_mode: record.charge_mode,
    amount_basis: record.amount_basis,
    summary: `${(record.summary || "").trim()}（续费）`.trim(),
    total_fee: Number(record.total_fee || 0),
    monthly_fee: Number(record.monthly_fee || 0),
    billing_cycle_text: record.billing_cycle_text || "",
    period_start_month: record.period_start_month ? shiftMonth(record.period_start_month, 12) : "",
    period_end_month: record.period_end_month ? shiftMonth(record.period_end_month, 12) : "",
    collection_start_date: record.collection_start_date ? shiftDateText(record.collection_start_date, 1) : "",
    due_month: record.due_month ? shiftDateText(record.due_month, 1) : "",
    payment_method: normalizePaymentMethod(record.payment_method),
    status: "FULL_ARREARS",
    received_amount: 0,
    note: `${(record.note || "").trim()} 续费自#${record.serial_no}`.trim(),
    extra_note: record.extra_note || "",
    color_tag: record.color_tag || "",
  };
}

function openRenewDialog(row: BillingRecord) {
  renewTargetRecord.value = row;
  renewRows.value = [buildRenewDraft(row)];
  showRenewDialog.value = true;
}

async function submitRenew() {
  if (!renewTargetRecord.value) return;
  const validationError = renewRows.value
    .map((item, index) => validateBillingDraft(item, index))
    .find((item) => item);
  if (validationError) {
    ElMessage.warning(validationError);
    return;
  }
  const draft = prepareBillingDraftsForSubmit(renewRows.value)[0];
  renewing.value = true;
  try {
    await apiClient.post(`/billing-records/${renewTargetRecord.value.id}/renew`, {
      charge_category: draft.charge_category,
      charge_mode: draft.charge_mode,
      amount_basis: draft.amount_basis,
      summary: draft.summary,
      total_fee: draft.total_fee,
      monthly_fee: draft.monthly_fee,
      billing_cycle_text: draft.billing_cycle_text,
      period_start_month: draft.period_start_month,
      period_end_month: draft.period_end_month,
      collection_start_date: draft.collection_start_date,
      due_month: draft.due_month,
      payment_method: draft.payment_method,
      status: draft.status,
      received_amount: draft.received_amount,
      note: draft.note,
      extra_note: draft.extra_note,
      color_tag: draft.color_tag,
    });
    ElMessage.success("续费记录已生成");
    showRenewDialog.value = false;
    renewTargetRecord.value = null;
    await fetchRecords();
    await fetchSummary();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "续费失败");
  } finally {
    renewing.value = false;
  }
}

function openCustomerDetail(record: BillingRecord) {
  void openLedgerView(record);
}

function openGrantSettings() {
  router.push({
    path: isMobileWorkflow.value ? "/m/admin/users" : "/admin/users",
    query: { tab: "grants" },
  });
}

function resetAssignmentForm() {
  Object.assign(assignmentForm, createBillingAssignmentForm());
}

async function fetchAssignments(recordId: number) {
  assignmentLoading.value = true;
  try {
    const resp = await apiClient.get<BillingAssignmentItem[]>(`/billing-records/${recordId}/assignees`);
    assignmentRows.value = resp.data;
  } catch (error) {
    ElMessage.error("获取执行分派失败");
    assignmentRows.value = [];
  } finally {
    assignmentLoading.value = false;
  }
}

async function openAssignmentDialog(record: BillingRecord) {
  assignmentTargetRecord.value = record;
  showAssignmentDialog.value = true;
  resetAssignmentForm();
  await fetchAssignableUsers();
  await fetchAssignments(record.id);
}

async function createAssignment() {
  if (!assignmentTargetRecord.value) return;
  if (!assignmentForm.assignee_user_id) {
    ElMessage.warning("请先选择执行人员");
    return;
  }
  assignmentSubmitting.value = true;
  try {
    await apiClient.post(`/billing-records/${assignmentTargetRecord.value.id}/assignees`, assignmentForm);
    ElMessage.success("执行分派已创建");
    resetAssignmentForm();
    await fetchAssignments(assignmentTargetRecord.value.id);
    await fetchRecords();
    await fetchSummary();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "创建执行分派失败");
  } finally {
    assignmentSubmitting.value = false;
  }
}

async function deactivateAssignment(item: BillingAssignmentItem) {
  if (!assignmentTargetRecord.value) return;
  try {
    await apiClient.patch(
      `/billing-records/${assignmentTargetRecord.value.id}/assignees/${item.id}`,
      { is_active: false },
    );
    ElMessage.success("已取消分派");
    await fetchAssignments(assignmentTargetRecord.value.id);
    await fetchRecords();
    await fetchSummary();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "取消分派失败");
  }
}

function resetSplitPaymentForm() {
  Object.assign(splitForm, createBillingSplitPaymentForm(todayInBrowserTimeZone()));
  splitAllocations.value = [];
  splitCustomerRecordCount.value = 0;
}

async function buildSplitSuggestions() {
  if (!splitTargetRecord.value?.customer_id) return;
  if (splitForm.amount <= 0) {
    ElMessage.warning("请先输入收款总额");
    return;
  }
  splitSuggestionLoading.value = true;
  try {
    const resp = await apiClient.post<BillingPaymentSuggestion>("/billing-records/payments/suggest", {
      customer_id: splitTargetRecord.value.customer_id,
      amount: splitForm.amount,
      strategy: splitForm.strategy,
    });
    splitCustomerRecordCount.value = resp.data.allocations.length;
    splitAllocations.value = resp.data.allocations.map((item) => ({
      billing_record_id: item.billing_record_id,
      serial_no: item.serial_no,
      summary: item.summary,
      due_month: item.due_month,
      outstanding_amount: Number(item.outstanding_amount || 0),
      allocated_amount: Number(item.suggested_amount || 0),
    }));
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "生成分摊建议失败");
    splitAllocations.value = [];
    splitCustomerRecordCount.value = 0;
  } finally {
    splitSuggestionLoading.value = false;
  }
}

async function openSplitPaymentDialog(record: BillingRecord) {
  if (!canWriteBillingRecord(record)) {
    ElMessage.warning("该客户处于临时只读授权范围，不能登记收款分摊");
    return;
  }
  if (!record.customer_id) {
    ElMessage.warning("该收费记录缺少客户信息，无法分摊收款");
    return;
  }
  splitTargetRecord.value = record;
  showSplitPaymentDialog.value = true;
  resetSplitPaymentForm();
}

function normalizeSplitAllocationValue(row: BillingSplitAllocationRow) {
  row.allocated_amount = Number(Math.max(0, Number(row.allocated_amount || 0)).toFixed(2));
}

async function submitSplitPayment() {
  if (!splitTargetRecord.value?.customer_id) return;
  if (!splitAllocations.value.length) {
    ElMessage.warning("请先生成分摊建议");
    return;
  }
  const validAllocations = splitAllocations.value
    .filter((item) => Number(item.allocated_amount || 0) > 0)
    .map((item) => ({
      billing_record_id: item.billing_record_id,
      allocated_amount: Number(item.allocated_amount),
    }));
  if (!validAllocations.length) {
    ElMessage.warning("请至少给一个项目分配金额");
    return;
  }
  if (Math.abs(splitRemainingAmount.value) > 0.01) {
    ElMessage.warning("分摊金额合计必须等于收款总额");
    return;
  }
  if (!splitForm.receipt_account.trim()) {
    ElMessage.warning("请选择入账账户");
    return;
  }

  splitSubmitting.value = true;
  try {
    await apiClient.post("/billing-records/payments", {
      customer_id: splitTargetRecord.value.customer_id,
      occurred_at: splitForm.occurred_at,
      amount: splitForm.amount,
      strategy: splitForm.strategy,
      receipt_account: splitForm.receipt_account,
      note: splitForm.note,
      allocations: validAllocations,
    });
    ElMessage.success("收款分摊已保存");
    showSplitPaymentDialog.value = false;
    await fetchRecords();
    await fetchSummary();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "保存收款分摊失败");
  } finally {
    splitSubmitting.value = false;
  }
}

function openTerminateDialog(row: BillingRecord) {
  terminateTargetRecord.value = row;
  Object.assign(terminateForm, createBillingTerminateForm(todayInBrowserTimeZone()), {
    reason: "提前终止合同",
  });
  showTerminateDialog.value = true;
}

async function submitTerminate() {
  if (!terminateTargetRecord.value) return;
  const normalizedTerminatedAt = normalizeDateText(terminateForm.terminated_at) ?? terminateForm.terminated_at;
  terminateForm.terminated_at = normalizedTerminatedAt;
  terminating.value = true;
  try {
    await apiClient.post(`/billing-records/${terminateTargetRecord.value.id}/terminate`, {
      terminated_at: normalizedTerminatedAt,
      reduced_fee: terminateForm.reduced_fee,
      reason: terminateForm.reason,
    });
    ElMessage.success("已终止合同并更新应收");
    showTerminateDialog.value = false;
    await fetchRecords();
    await fetchSummary();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "终止合同失败");
  } finally {
    terminating.value = false;
  }
}

async function fetchLedgerData() {
  if (!ledgerTargetRecord.value?.customer_id) return;
  const customerId = ledgerTargetRecord.value.customer_id;
  const cacheKey = `${customerId}:${ledgerDateRange.value?.[0] || ""}:${ledgerDateRange.value?.[1] || ""}`;
  const cached = ledgerCache.get(cacheKey);
  if (cached) {
    ledgerData.value = cached;
    return;
  }
  ledgerLoading.value = true;
  try {
    const params: Record<string, string | number> = { customer_id: customerId };
    if (ledgerDateRange.value?.[0]) {
      params.date_from = ledgerDateRange.value[0];
    }
    if (ledgerDateRange.value?.[1]) {
      params.date_to = ledgerDateRange.value[1];
    }
    const resp = await apiClient.get<BillingLedgerData>("/billing-records/ledger", { params });
    ledgerCache.set(cacheKey, resp.data);
    ledgerData.value = resp.data;
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "加载客户明细账失败");
    ledgerData.value = null;
  } finally {
    ledgerLoading.value = false;
  }
}

async function prefetchLedgerRows(records: BillingRecord[]) {
  const topRows = records.filter((item) => item.customer_id).slice(0, 3);
  await Promise.all(
    topRows.map(async (row) => {
      const customerId = row.customer_id;
      if (!customerId) return;
      const cacheKey = `${customerId}::`;
      if (ledgerCache.has(cacheKey)) return;
      try {
        const resp = await apiClient.get<BillingLedgerData>("/billing-records/ledger", {
          params: { customer_id: customerId },
        });
        ledgerCache.set(cacheKey, resp.data);
      } catch {
        // Ignore background prefetch failures.
      }
    }),
  );
}

function openReceiptReconciliation() {
  router.push({
    path: isMobileWorkflow.value ? "/m/receipt-reconciliation" : "/receipt-reconciliation",
    query: {
      account: filters.receipt_account || undefined,
      month: filters.billing_month || undefined,
    },
  });
}

async function drillDownLedgerMonth(monthText: string) {
  const range = getMonthDateRange(monthText);
  if (!range) {
    ElMessage.warning("月份格式无效，无法下钻");
    return;
  }
  ledgerDateRange.value = range;
  await fetchLedgerData();
}

async function resetLedgerDateFilter() {
  ledgerDateRange.value = null;
  await fetchLedgerData();
}

async function openLedgerView(row: BillingRecord) {
  if (!row.customer_id) {
    ElMessage.warning("该收费记录缺少客户信息，无法查看明细账");
    return;
  }
  ledgerTargetRecord.value = row;
  ledgerDateRange.value = null;
  ledgerData.value = null;
  await fetchLedgerData();
  if (isMobile.value) {
    showLedgerDialog.value = true;
    return;
  }
  await nextTick();
  ledgerPanelAnchor.value?.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function openLedgerDialog(row: BillingRecord) {
  await openLedgerView(row);
}

function clearLedgerPanel() {
  ledgerTargetRecord.value = null;
  ledgerDateRange.value = null;
  ledgerData.value = null;
}

function resetMobileFilters() {
  Object.assign(filters, createBillingFilters());
  billingQuickView.value = "ALL";
  billingMobileFilterMemory.clearState();
  void runBillingQuery();
}

function restoreSavedBillingFilters() {
  billingMobileFilterMemory.restoreSavedState((snapshot) => {
    const { quick_view, ...rest } = snapshot;
    Object.assign(filters, createBillingFilters(), rest);
    billingQuickView.value =
      quick_view === "OVERDUE" || quick_view === "DUE_SOON" || quick_view === "OPEN" || quick_view === "CLEARED"
        ? quick_view
        : "ALL";
  });
}

function setBillingQuickView(view: BillingQuickView) {
  billingQuickView.value = view;
  if (isMobileWorkflow.value) {
    billingMobileFilterMemory.saveState(currentBillingFilterSnapshot());
  }
}

function removeBillingFilterChip(
  key: "keyword" | "customer_id" | "billing_month" | "receipt_account" | "contact_name" | "payment_method" | "status",
) {
  if (key === "keyword") filters.keyword = "";
  if (key === "customer_id") filters.customer_id = null;
  if (key === "billing_month") filters.billing_month = "";
  if (key === "receipt_account") filters.receipt_account = "";
  if (key === "contact_name") filters.contact_name = "";
  if (key === "payment_method") filters.payment_method = "";
  if (key === "status") filters.status = "";
  void runBillingQuery();
}

function toggleExpandedBilling(recordId: number) {
  expandedBillingId.value = expandedBillingId.value === recordId ? null : recordId;
}

function mobileRowTone(row: BillingRecord): "" | "warning" | "danger" | "settled" {
  if (row.status === "CLEARED" || Number(row.outstanding_amount || 0) <= 0) return "settled";
  const days = getDaysUntilDue(row.due_month || "");
  if (days !== null && days < 0) return "danger";
  if (days !== null && days <= 7) return "warning";
  return "";
}

function mobileDueTagType(row: BillingRecord): "" | "success" | "warning" | "danger" | "info" {
  if (row.status === "CLEARED" || Number(row.outstanding_amount || 0) <= 0) return "success";
  const days = getDaysUntilDue(row.due_month || "");
  if (days !== null && days < 0) return "danger";
  if (days !== null && days <= 7) return "warning";
  return "info";
}

function mobileDueText(row: BillingRecord): string {
  const due = (row.due_month || "").trim();
  if (!due) return "无到期日";
  if (row.status === "CLEARED") return `已清账 · ${due}`;
  const date = new Date(`${due}T00:00:00`);
  if (Number.isNaN(date.getTime())) return due;
  const today = new Date(`${todayInBrowserTimeZone()}T00:00:00`);
  const diffDays = Math.round((date.getTime() - today.getTime()) / 86400000);
  if (diffDays < 0) return `已逾期 ${Math.abs(diffDays)} 天`;
  if (diffDays === 0) return "今天到期";
  if (diffDays <= 7) return `${diffDays} 天后到期`;
  return due;
}

function mobileRowBalanceText(row: BillingRecord): string {
  if (row.status === "CLEARED" || Number(row.outstanding_amount || 0) <= 0) {
    return `已收 ${formatAmount(row.received_amount)}`;
  }
  return `余额 ${formatAmount(row.outstanding_amount)}`;
}

function mobileRowAmountMeta(row: BillingRecord): string {
  return `应收 ${formatAmount(row.total_fee)} · 实收 ${formatAmount(row.received_amount)}`;
}

function mobileRowBusinessMeta(row: BillingRecord): string {
  return [
    statusLabel(row.status),
    normalizePaymentMethod(row.payment_method),
    row.receivable_period_text || "-",
    row.accountant_username || "-",
  ]
    .filter(Boolean)
    .join(" · ");
}

function mobileLatestPaymentText(row: BillingRecord): string {
  if (!row.latest_payment_at || Number(row.latest_payment_amount || 0) <= 0) return "-";
  return `${row.latest_payment_at} · ${formatAmount(row.latest_payment_amount)}`;
}

function handleBillingMenuCommand(command: string, row: BillingRecord) {
  if (command === "ledger") void openLedgerDialog(row);
  if (command === "split") void openSplitPaymentDialog(row);
  if (command === "execution") void openExecutionDrawer(row);
  if (command === "activity") void openActivityDrawer(row);
  if (command === "assignment") void openAssignmentDialog(row);
  if (command === "renew") openRenewDialog(row);
  if (command === "terminate") openTerminateDialog(row);
}

function openBillingRowActions(row: BillingRecord) {
  selectedBillingActionRow.value = row;
  showBillingRowActionSheet.value = true;
}

function handleBillingRowActionSelect(action: string) {
  if (!selectedBillingActionRow.value) return;
  handleBillingMenuCommand(action, selectedBillingActionRow.value);
}

async function handleRouteAction() {
  if (routeActionHandling.value) return;
  const action = String(route.query.action || "").trim();
  const recordIdToken = String(route.query.record_id || "").trim();
  if (!action || !recordIdToken) return;

  routeActionHandling.value = true;
  try {
    const recordId = Number(recordIdToken);
    if (!Number.isFinite(recordId) || recordId <= 0) return;
    let target = rows.value.find((item) => item.id === recordId) ?? null;
    if (!target) {
      await fetchRecords();
      target = rows.value.find((item) => item.id === recordId) ?? null;
    }
    if (!target) {
      ElMessage.warning("待办对应收费记录不存在或当前不可见");
      return;
    }
    if (action === "renew") {
      if (!canManageBillingLifecycle.value) {
        ElMessage.warning("当前账号无续费权限");
        return;
      }
      openRenewDialog(target);
      return;
    }
  } finally {
    const nextQuery = { ...route.query };
    delete nextQuery.action;
    delete nextQuery.record_id;
    await router.replace({ path: route.path, query: nextQuery });
    routeActionHandling.value = false;
  }
}

async function handleBillingRouteQueue() {
  if (billingRouteQueueHandling.value || !isMobileWorkflow.value) return;
  const queue = String(route.query.queue || "").trim();
  if (queue !== "activity") return;

  billingRouteQueueHandling.value = true;
  try {
    Object.assign(filters, createBillingFilters());
    billingQuickView.value = "OPEN";
    await Promise.all([fetchRecords(), fetchSummary()]);

    const nextQuery = { ...route.query };
    delete nextQuery.queue;
    await router.replace({ path: route.path, query: nextQuery });

    if (!billingActivityQueueRows.value.length) {
      ElMessage.warning("当前没有可连续处理的收费单");
      return;
    }
    startBillingActivityQueue();
  } finally {
    billingRouteQueueHandling.value = false;
  }
}

function resetExecutionForm() {
  Object.assign(executionForm, createBillingExecutionForm(todayInBrowserTimeZone()));
}

async function fetchExecutionLogs(recordId: number) {
  executionLoading.value = true;
  try {
    const resp = await apiClient.get<BillingExecutionLogItem[]>(`/billing-records/${recordId}/execution-logs`);
    executionRows.value = resp.data;
  } catch (error) {
    ElMessage.error("获取执行进度失败");
    executionRows.value = [];
  } finally {
    executionLoading.value = false;
  }
}

async function openExecutionDrawer(record: BillingRecord) {
  executionTargetRecord.value = record;
  showExecutionDrawer.value = true;
  resetExecutionForm();
  await fetchExecutionLogs(record.id);
}

async function submitExecutionLog() {
  if (!executionTargetRecord.value) return;
  if (!executionForm.content.trim()) {
    ElMessage.warning("请填写执行进度内容");
    return;
  }
  executionSubmitting.value = true;
  try {
    await apiClient.post(`/billing-records/${executionTargetRecord.value.id}/execution-logs`, executionForm);
    ElMessage.success("执行进度已保存");
    resetExecutionForm();
    await fetchExecutionLogs(executionTargetRecord.value.id);
  } catch (error: any) {
    const detail = error?.response?.data?.detail;
    if (error?.response?.status === 403) {
      ElMessage.error("当前账号仅可查看，不能写入执行进度");
    } else {
      ElMessage.error(detail ?? "保存执行进度失败");
    }
  } finally {
    executionSubmitting.value = false;
  }
}

function resetActivityForm() {
  Object.assign(activityForm, createBillingActivityForm(todayInBrowserTimeZone()));
}

function onActivityTypeChange(value: unknown) {
  const paymentMode = isPaymentActivityType(value);
  activityForm.activity_type = paymentMode ? "PAYMENT" : "REMINDER";
  if (!paymentMode) {
    activityForm.amount = 0;
    activityForm.payment_nature = "";
    activityForm.receipt_account = "未指定";
    activityForm.is_prepay = false;
    activityForm.is_settlement = false;
  }
}

async function fetchActivities() {
  if (!selectedRecord.value) return;
  activityLoading.value = true;
  try {
    const resp = await apiClient.get<BillingActivity[]>(
      `/billing-records/${selectedRecord.value.id}/activities`,
    );
    activityRows.value = resp.data;
  } catch (error) {
    ElMessage.error("获取催收/收款记录失败");
    activityRows.value = [];
  } finally {
    activityLoading.value = false;
  }
}

async function openActivityDrawer(record: BillingRecord) {
  if (!canWriteBillingRecord(record)) {
    ElMessage.warning("该客户处于临时只读授权范围，不能新增催收/收款日志");
    return;
  }
  selectedRecord.value = record;
  showActivityDrawer.value = true;
  resetActivityForm();
  await fetchActivities();
}

function getNextBillingActivityRecordId(currentRecordId: number) {
  const currentIndex = billingActivityQueueRows.value.findIndex((item) => item.id === currentRecordId);
  if (currentIndex < 0 || currentIndex >= billingActivityQueueRows.value.length - 1) return null;
  return billingActivityQueueRows.value[currentIndex + 1]?.id ?? null;
}

function startBillingActivityQueue() {
  const firstRecord = billingActivityQueueRows.value[0];
  if (!firstRecord) {
    ElMessage.warning("当前没有可连续处理的收费单");
    return;
  }
  void openActivityDrawer(firstRecord);
}

async function submitActivity(mode: "close" | "next" = "close") {
  if (!selectedRecord.value) return;
  if (!canWriteBillingRecord(selectedRecord.value)) {
    ElMessage.warning("该客户处于临时只读授权范围，不能新增催收/收款日志");
    return;
  }
  const normalizedType = normalizeActivityType(activityForm.activity_type);
  const paymentMode = normalizedType === "PAYMENT";
  activityForm.activity_type = normalizedType;
  if (!activityForm.content.trim()) {
    ElMessage.warning("请填写沟通内容");
    return;
  }
  if (paymentMode && activityForm.amount <= 0) {
    ElMessage.warning("收款金额必须大于 0");
    return;
  }
  if (paymentMode && !activityForm.receipt_account.trim()) {
    ElMessage.warning("请选择入账账户");
    return;
  }
  const payload =
    paymentMode
      ? { ...activityForm, activity_type: "PAYMENT" as const }
      : {
          ...activityForm,
          activity_type: "REMINDER" as const,
          amount: 0,
          payment_nature: "",
          receipt_account: "",
          is_prepay: false,
          is_settlement: false,
        };
  const currentRecordId = selectedRecord.value.id;
  const nextRecordId = mode === "next" ? getNextBillingActivityRecordId(currentRecordId) : null;
  try {
    await apiClient.post(`/billing-records/${currentRecordId}/activities`, payload);
    resetActivityForm();
    await fetchActivities();
    await fetchRecords();
    await fetchSummary();
    if (mode === "next" && nextRecordId && isMobileWorkflow.value) {
      const nextRecord = rows.value.find((item) => item.id === nextRecordId);
      if (nextRecord && canWriteBillingRecord(nextRecord) && Number(nextRecord.outstanding_amount || 0) > 0) {
        ElMessage.success("记录已保存，已切到下一条");
        await openActivityDrawer(nextRecord);
        return;
      }
    }
    ElMessage.success(mode === "next" ? "记录已保存，已到最后一条" : "记录已保存");
  } catch (error) {
    ElMessage.error("保存失败");
  }
}

onMounted(async () => {
  if (isMobileWorkflow.value) {
    restoreSavedBillingFilters();
  }
  await runBillingQuery();
  void fetchCustomers();
  await handleRouteAction();
  await handleBillingRouteQueue();
});

watch(
  () => route.fullPath,
  () => {
    void handleRouteAction();
    void handleBillingRouteQueue();
  },
);
</script>

<template>
  <template v-if="isMobileWorkflow">
    <section class="mobile-page billing-mobile-page">
      <section class="mobile-shell-panel billing-mobile-focus-panel" v-loading="summaryLoading && billingSummaryHydrated">
        <template v-if="showBillingSummarySkeleton">
          <div class="billing-mobile-summary-head">
            <div class="mobile-skeleton-stack billing-mobile-skeleton-copy">
              <div class="mobile-skeleton-line is-md"></div>
              <div class="mobile-skeleton-line is-xl"></div>
            </div>
            <div class="mobile-skeleton-button"></div>
          </div>

          <div class="billing-mobile-skeleton-balance">
            <div class="mobile-skeleton-stack">
              <div class="mobile-skeleton-line is-xs"></div>
              <div class="mobile-skeleton-line is-lg"></div>
            </div>
            <div class="billing-mobile-skeleton-meta">
              <div v-for="index in 3" :key="`billing-meta-${index}`" class="mobile-skeleton-line is-sm"></div>
            </div>
          </div>

          <div class="billing-mobile-stats">
            <div v-for="index in 3" :key="`billing-stat-${index}`" class="billing-mobile-skeleton-stat">
              <div class="mobile-skeleton-line is-xs"></div>
              <div class="mobile-skeleton-line is-sm"></div>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="billing-mobile-summary-head">
            <div>
              <div class="billing-mobile-title">{{ mobileFocusSummary.title }}</div>
              <div class="billing-mobile-copy">{{ mobileFocusSummary.detail }}</div>
            </div>
            <el-button
              v-if="canViewReceiptLedger"
              text
              size="small"
              type="primary"
              @click="openReceiptReconciliation"
            >
              到账核对
            </el-button>
          </div>

          <div class="billing-mobile-balance-strip" :class="mobileFocusSummary.tone">
            <div class="billing-mobile-balance-main">
              <span>未收合计</span>
              <strong>{{ formatAmount(visibleOutstandingTotal) }}</strong>
            </div>
            <div class="billing-mobile-balance-meta">
              <span v-for="item in mobileHeadlineStats" :key="item">{{ item }}</span>
            </div>
          </div>

          <div class="billing-mobile-stats">
            <article
              v-for="item in mobileSummaryCards"
              :key="item.label"
              class="billing-mobile-stat"
              :class="{ accent: item.accent, warning: item.warning, danger: item.danger }"
            >
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </article>
          </div>
        </template>
      </section>

      <section class="mobile-shell-panel">
        <div class="mobile-toolbar">
          <div class="mobile-toolbar-main">
            <el-input
              v-model="filters.keyword"
              placeholder="公司 / 项目 / 备注"
              clearable
              @keyup.enter="runBillingQuery"
            />
          </div>
          <div class="mobile-toolbar-actions">
            <el-button class="mobile-row-secondary-button" plain :icon="Filter" @click="showMobileFilters = true">
              筛选
            </el-button>
            <el-button class="mobile-row-primary-button" type="primary" @click="openCreateDialog">新增收费单</el-button>
          </div>
        </div>
        <div class="mobile-filter-presets">
          <button
            v-for="item in billingQuickFilters"
            :key="item.key"
            type="button"
            class="mobile-filter-preset"
            :class="{ active: billingQuickView === item.key }"
            @click="setBillingQuickView(item.key)"
          >
            <span>{{ item.label }}</span>
            <strong>{{ item.count }}</strong>
          </button>
        </div>
        <div v-if="activeFilterChips.length" class="mobile-chip-row billing-mobile-chip-row">
          <button
            v-for="chip in billingFilterChips"
            :key="chip.key"
            type="button"
            class="mobile-chip-button"
            @click="removeBillingFilterChip(chip.key)"
          >
            <span>{{ chip.label }}</span>
            <span class="mobile-chip-close">移除</span>
          </button>
          <button type="button" class="billing-clear-chip" @click="resetMobileFilters">清空</button>
        </div>
      </section>

      <section class="mobile-shell-panel billing-mobile-list-panel">
        <div v-if="billingActivityQueueRows.length" class="mobile-queue-strip">
          <div class="mobile-queue-main">
            <div class="mobile-queue-kicker">连续催收</div>
            <div class="mobile-queue-copy">按当前筛选顺序处理 {{ billingActivityQueueRows.length }} 条待跟进收费单。</div>
          </div>
          <el-button class="mobile-row-secondary-button" size="small" plain @click="startBillingActivityQueue">
            从首条开始
          </el-button>
        </div>
        <div class="billing-mobile-list-head">
          <div class="billing-mobile-title">{{ billingListTitle }}</div>
          <div v-if="showBillingListInitialSkeleton" class="mobile-skeleton-chip billing-mobile-count-skeleton"></div>
          <el-tag v-else class="mobile-count-tag" size="small" effect="plain">{{ billingVisibleRows.length }} 条</el-tag>
        </div>

        <div v-loading="loading && billingListHydrated" class="billing-mobile-list">
          <template v-if="showBillingListInitialSkeleton">
            <article v-for="index in 4" :key="`billing-skeleton-${index}`" class="billing-mobile-row billing-mobile-skeleton-row">
              <div class="billing-mobile-row-top">
                <div class="billing-mobile-row-head billing-mobile-skeleton-copy">
                  <div class="mobile-skeleton-line is-lg"></div>
                  <div class="mobile-skeleton-line is-md"></div>
                </div>
                <div class="mobile-skeleton-chip"></div>
              </div>
              <div class="mobile-skeleton-stack">
                <div class="mobile-skeleton-line is-md"></div>
                <div class="mobile-skeleton-line is-xl"></div>
              </div>
              <div class="billing-mobile-skeleton-actions">
                <div class="mobile-skeleton-button"></div>
                <div class="mobile-skeleton-button"></div>
                <div class="mobile-skeleton-button"></div>
              </div>
            </article>
          </template>
          <div v-else-if="!billingVisibleRows.length" class="mobile-empty-block">
            <div class="mobile-empty-kicker">收费明细</div>
            <div class="mobile-empty-title">当前没有匹配的收费单</div>
            <div class="mobile-empty-copy">切换快速视图、客户或账户筛选，继续定位待处理收费单。</div>
          </div>
          <article
            v-for="row in billingVisibleRows"
            :key="row.id"
            class="billing-mobile-row"
            :class="mobileRowTone(row)"
          >
            <div class="billing-mobile-row-top">
              <div class="billing-mobile-row-head">
                <button type="button" class="billing-mobile-name" @click="openLedgerDialog(row)">
                  {{ row.customer_name }}
                </button>
                <div class="billing-mobile-summary">{{ row.summary || row.charge_category || "代账" }}</div>
              </div>
              <el-tag class="mobile-status-tag" size="small" effect="plain" :type="mobileDueTagType(row)">
                {{ mobileDueText(row) }}
              </el-tag>
            </div>

            <div class="billing-mobile-amount-line">
              <strong class="billing-mobile-balance-value">{{ mobileRowBalanceText(row) }}</strong>
              <span>{{ mobileRowAmountMeta(row) }}</span>
            </div>

            <div class="billing-mobile-meta">
              {{ mobileRowBusinessMeta(row) }}
            </div>

            <transition name="billing-expand">
              <div v-if="expandedBillingId === row.id" class="billing-mobile-expanded">
                <div class="billing-mobile-extra-grid">
                  <div class="billing-mobile-extra-item">
                    <span>到期提醒</span>
                    <strong>{{ mobileDueText(row) }}</strong>
                  </div>
                  <div class="billing-mobile-extra-item">
                    <span>最近收款</span>
                    <strong>{{ mobileLatestPaymentText(row) }}</strong>
                  </div>
                  <div class="billing-mobile-extra-item">
                    <span>入账账户</span>
                    <strong>{{ row.latest_receipt_account || "-" }}</strong>
                  </div>
                  <div class="billing-mobile-extra-item">
                    <span>联系人</span>
                    <strong>{{ row.customer_contact_name || "-" }}</strong>
                  </div>
                </div>
                <div v-if="row.note || row.extra_note" class="billing-mobile-note">
                  {{ [row.note, row.extra_note].filter(Boolean).join(" · ") }}
                </div>
              </div>
            </transition>

            <div class="billing-mobile-actions">
              <div class="mobile-action-main">
                <el-button
                  class="mobile-row-primary-button"
                  size="small"
                  type="primary"
                  :disabled="!canWriteBillingRecord(row)"
                  @click="openActivityDrawer(row)"
                >
                  催收/收款
                </el-button>
                <el-button class="mobile-row-secondary-button" size="small" plain @click="openExecutionDrawer(row)">
                  执行进度
                </el-button>
                <el-button class="mobile-row-secondary-button" size="small" plain @click="openLedgerDialog(row)">
                  往来账
                </el-button>
              </div>
              <div class="mobile-action-sub">
                <button type="button" class="mobile-action-link is-muted" @click="toggleExpandedBilling(row.id)">
                  {{ expandedBillingId === row.id ? "收起补充信息" : "展开补充信息" }}
                </button>
                <button
                  v-if="canManageBillingLifecycle"
                  type="button"
                  class="mobile-action-link"
                  @click="openRenewDialog(row)"
                >
                  确认续费
                </button>
                <button type="button" class="mobile-action-link" @click="openBillingRowActions(row)">更多操作</button>
              </div>
            </div>
          </article>
        </div>
      </section>
    </section>

    <MobileFilterSheet
      v-model="showMobileFilters"
      title="筛选收费单"
      subtitle="筛完直接应用，优先看逾期和近期待收。"
      :summary-items="activeFilterChips"
      empty-summary="当前未设置筛选条件"
      size="82vh"
    >
      <el-form label-position="top" class="billing-mobile-filter-form">
        <div v-if="billingMobileFilterMemory.hasSavedState.value" class="mobile-filter-restore">
          <el-button text type="primary" @click="restoreSavedBillingFilters">恢复上次已应用条件</el-button>
        </div>
        <el-form-item label="关键词">
          <el-input
            v-model="filters.keyword"
            placeholder="公司 / 项目 / 备注"
            clearable
            @keyup.enter="runBillingQuery"
          />
        </el-form-item>
        <el-form-item label="客户">
          <el-select v-model="filters.customer_id" filterable clearable placeholder="全部客户">
            <el-option
              v-for="item in customerFilterOptions"
              :key="`mobile-customer-${item.id}`"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="账务月份">
          <el-date-picker
            v-model="filters.billing_month"
            type="month"
            value-format="YYYY-MM"
            format="YYYY-MM"
            placeholder="全部月份"
            clearable
          />
        </el-form-item>
        <el-form-item label="入账账户">
          <el-select v-model="filters.receipt_account" clearable filterable placeholder="全部账户">
            <el-option
              v-for="item in receiptAccountOptions"
              :key="`mobile-filter-account-${item.value}`"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="联系人">
          <el-input
            v-model="filters.contact_name"
            placeholder="客户联系人"
            clearable
            @keyup.enter="runBillingQuery"
          />
        </el-form-item>
        <el-form-item label="付款方式">
          <el-select v-model="filters.payment_method" placeholder="全部" clearable>
            <el-option label="预收" value="预收" />
            <el-option label="后收" value="后收" />
          </el-select>
        </el-form-item>
        <el-form-item label="台账状态">
          <el-select v-model="filters.status" placeholder="全部" clearable>
            <el-option label="清账" value="CLEARED" />
            <el-option label="全欠" value="FULL_ARREARS" />
            <el-option label="部分收费" value="PARTIAL" />
          </el-select>
        </el-form-item>
        <el-button v-if="canManageGrant" plain @click="openGrantSettings">数据授权配置</el-button>
      </el-form>
      <template #footer>
        <el-button @click="resetMobileFilters">重置</el-button>
        <el-button type="primary" @click="showMobileFilters = false; runBillingQuery()">应用筛选</el-button>
      </template>
    </MobileFilterSheet>

    <MobileActionSheet
      v-model="showBillingRowActionSheet"
      title="收费单操作"
      :subtitle="selectedBillingActionRow ? `${selectedBillingActionRow.customer_name} · ${selectedBillingActionRow.summary || selectedBillingActionRow.charge_category || '代账'}` : ''"
      :items="billingRowActionItems"
      @select="handleBillingRowActionSelect"
    />
  </template>

  <el-space v-else direction="vertical" fill :size="12">
    <BillingSummaryPanel
      :summary="summary"
      :rows="rows"
      :payment-method-distribution="paymentMethodDistributionNormalized"
      :receipt-account-distribution="summary.receipt_account_distribution"
      :can-view-receipt-ledger="canViewReceiptLedger"
      @open-receipt-ledger="openReceiptReconciliation"
    />

    <BillingFilterCard
      :filters="filters"
      :can-manage-grant="canManageGrant"
      :customers="customerFilterOptions"
      :receipt-account-options="receiptAccountOptions"
      @query="runBillingQuery"
      @create="openCreateDialog"
      @grant="openGrantSettings"
    />
    <BillingRecordsCard
      :loading="loading"
      :rows="rows"
      :active-customer-id="ledgerTargetRecord?.customer_id ?? null"
      :can-manage-assignment="canManageAssignment"
      :can-manage-lifecycle="canManageBillingLifecycle"
      :can-write-record="canWriteBillingRecord"
      @customer="openCustomerDetail"
      @ledger="openLedgerDialog"
      @split="openSplitPaymentDialog"
      @execution="openExecutionDrawer"
      @activity="openActivityDrawer"
      @assignment="openAssignmentDialog"
      @renew="openRenewDialog"
      @terminate="openTerminateDialog"
    />
    <div ref="ledgerPanelAnchor">
      <BillingLedgerPanel
        v-if="ledgerTargetRecord && !isMobile"
        v-model:date-range="ledgerDateRange"
        :target-record="ledgerTargetRecord"
        :loading="ledgerLoading"
        :has-date-filter="ledgerHasDateFilter"
        :data="ledgerData"
        @query="fetchLedgerData"
        @reset="resetLedgerDateFilter"
        @clear="clearLedgerPanel"
        @drill-month="drillDownLedgerMonth"
      />
    </div>
  </el-space>
  <BillingCreateDialog
    :visible="showCreateDialog"
    :customer-id="createCustomerId"
    :customers="customers"
    :rows="createRows"
    @update:visible="showCreateDialog = $event"
    @update:customer-id="createCustomerId = $event"
    @update:rows="updateCreateRows"
    @submit="createRecord"
  />
  <BillingRenewDialog
    :visible="showRenewDialog"
    :target-record="renewTargetRecord"
    :rows="renewRows"
    :loading="renewing"
    @update:visible="showRenewDialog = $event"
    @update:rows="updateRenewRows"
    @closed="renewTargetRecord = null"
    @submit="submitRenew"
  />

  <BillingLedgerDialog
    v-model:visible="showLedgerDialog"
    v-model:date-range="ledgerDateRange"
    :target-record="ledgerTargetRecord"
    :loading="ledgerLoading"
    :has-date-filter="ledgerHasDateFilter"
    :data="ledgerData"
    @query="fetchLedgerData"
    @reset="resetLedgerDateFilter"
    @drill-month="drillDownLedgerMonth"
  />

  <BillingSplitPaymentDialog
    v-model:visible="showSplitPaymentDialog"
    :target-record="splitTargetRecord"
    :form="splitForm"
    :allocations="splitAllocations"
    :customer-record-count="splitCustomerRecordCount"
    :allocated-total="splitAllocatedTotal"
    :remaining-amount="splitRemainingAmount"
    :suggestion-loading="splitSuggestionLoading"
    :submitting="splitSubmitting"
    @normalize-allocation="normalizeSplitAllocationValue"
    @build-suggestions="buildSplitSuggestions"
    @submit="submitSplitPayment"
  />

  <BillingTerminateDialog
    v-model:visible="showTerminateDialog"
    :target-record="terminateTargetRecord"
    :form="terminateForm"
    :submitting="terminating"
    @submit="submitTerminate"
  />

  <BillingAssignmentDialog
    v-model:visible="showAssignmentDialog"
    :target-record="assignmentTargetRecord"
    :form="assignmentForm"
    :users="assignableUsers"
    :loading="assignmentLoading"
    :submitting="assignmentSubmitting"
    :rows="assignmentRows"
    @submit="createAssignment"
    @deactivate="deactivateAssignment"
  />

  <BillingExecutionDrawer
    v-model:visible="showExecutionDrawer"
    :target-record="executionTargetRecord"
    :form="executionForm"
    :submitting="executionSubmitting"
    :loading="executionLoading"
    :rows="executionRows"
    @submit="submitExecutionLog"
  />

  <BillingActivityDrawer
    v-model:visible="showActivityDrawer"
    :target-record="selectedRecord"
    :form="activityForm"
    :loading="activityLoading"
    :rows="activityRows"
    :queue-label="isMobileWorkflow ? billingActivityQueueLabel : ''"
    :show-next-action="isMobileWorkflow && hasNextBillingActivityRecord"
    @activity-type-change="onActivityTypeChange"
    @submit="submitActivity()"
    @submit-next="submitActivity('next')"
  />
</template>

<style scoped>
.billing-mobile-page {
  gap: 12px;
}

.billing-mobile-focus-panel {
  overflow: hidden;
}

.billing-mobile-summary-head,
.billing-mobile-list-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.billing-mobile-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.billing-mobile-copy {
  margin-top: 3px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--app-text-muted);
}

.billing-mobile-skeleton-copy {
  min-width: 0;
  flex: 1;
}

.billing-mobile-skeleton-balance {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
  padding: 14px;
  border: 1px solid var(--app-border-soft);
  background: rgba(255, 255, 255, 0.88);
}

.billing-mobile-skeleton-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
}

.billing-mobile-skeleton-stat {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px;
  border: 1px solid var(--app-border-soft);
  background: var(--app-bg-soft);
}

.billing-mobile-count-skeleton {
  flex-shrink: 0;
}

.billing-mobile-balance-strip {
  margin-top: 12px;
  padding: 14px;
  border: 1px solid rgba(77, 128, 150, 0.18);
  background:
    linear-gradient(135deg, rgba(77, 128, 150, 0.14), rgba(255, 255, 255, 0.96)),
    var(--app-bg-soft);
}

.billing-mobile-balance-strip.warning {
  border-color: rgba(198, 138, 24, 0.2);
  background: linear-gradient(135deg, rgba(198, 138, 24, 0.14), rgba(255, 255, 255, 0.96));
}

.billing-mobile-balance-strip.danger {
  border-color: rgba(187, 77, 77, 0.18);
  background: linear-gradient(135deg, rgba(187, 77, 77, 0.14), rgba(255, 255, 255, 0.96));
}

.billing-mobile-balance-main {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.billing-mobile-balance-main span {
  font-size: 12px;
  color: var(--app-text-muted);
}

.billing-mobile-balance-main strong {
  font-size: 30px;
  line-height: 0.95;
  color: var(--app-text-primary);
}

.billing-mobile-balance-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  margin-top: 10px;
  font-size: 12px;
  color: var(--app-text-muted);
}

.billing-mobile-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
}

.billing-mobile-stat {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px;
  border: 1px solid var(--app-border-soft);
  background: var(--app-bg-soft);
}

.billing-mobile-stat.accent {
  background: rgba(77, 128, 150, 0.1);
}

.billing-mobile-stat.warning {
  background: rgba(198, 138, 24, 0.08);
}

.billing-mobile-stat.danger {
  background: rgba(187, 77, 77, 0.08);
}

.billing-mobile-stat span {
  font-size: 11px;
  color: var(--app-text-muted);
}

.billing-mobile-stat strong {
  font-size: 16px;
  line-height: 1;
  color: var(--app-text-primary);
}

.billing-mobile-chip-row {
  margin-top: 12px;
}

.billing-clear-chip {
  border: none;
  background: transparent;
  padding: 0;
  color: var(--app-accent-strong);
  font-size: 12px;
}

.billing-mobile-list-panel {
  padding-top: 12px;
}

.billing-mobile-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 14px;
}

.billing-mobile-skeleton-row {
  gap: 10px;
}

.billing-mobile-skeleton-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.billing-mobile-row {
  border-top: 1px solid var(--app-border-soft);
  padding: 12px 0 0;
}

.billing-mobile-row.warning {
  border-top-color: rgba(198, 138, 24, 0.22);
}

.billing-mobile-row.danger {
  border-top-color: rgba(187, 77, 77, 0.22);
}

.billing-mobile-row.settled {
  opacity: 0.82;
}

.billing-mobile-row:first-child {
  border-top: none;
  padding-top: 0;
}

.billing-mobile-row-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.billing-mobile-row-head {
  min-width: 0;
  flex: 1;
}

.billing-mobile-name {
  border: none;
  padding: 0;
  background: transparent;
  text-align: left;
  font-size: 15px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.billing-mobile-summary {
  margin-top: 4px;
  font-size: 13px;
  color: var(--app-text-secondary);
}

.billing-mobile-amount-line {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  align-items: baseline;
  margin-top: 8px;
}

.billing-mobile-balance-value {
  font-size: 18px;
  color: var(--app-text-primary);
}

.billing-mobile-amount-line span {
  font-size: 12px;
  color: var(--app-text-muted);
}

.billing-mobile-meta {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--app-text-muted);
}

.billing-mobile-expanded {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--app-border-soft);
}

.billing-mobile-extra-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.billing-mobile-extra-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px;
  background: var(--app-bg-soft);
}

.billing-mobile-extra-item span {
  font-size: 11px;
  color: var(--app-text-muted);
}

.billing-mobile-extra-item strong {
  font-size: 13px;
  line-height: 1.4;
  color: var(--app-text-primary);
}

.billing-mobile-note {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.55;
  color: var(--app-text-secondary);
}

.billing-mobile-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}

.billing-mobile-filter-form :deep(.el-form-item) {
  margin-bottom: 14px;
}

.mobile-filter-restore {
  display: flex;
  justify-content: flex-start;
  margin-bottom: 6px;
}

.billing-expand-enter-active,
.billing-expand-leave-active {
  transition: opacity 180ms ease, transform 180ms ease;
}

.billing-expand-enter-from,
.billing-expand-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

@media (max-width: 420px) {
  .billing-mobile-stats,
  .billing-mobile-extra-grid {
    grid-template-columns: 1fr;
  }
}
</style>
