<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, nextTick, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { apiClient } from "../api/client";
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
import { useResponsive } from "../composables/useResponsive";
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
} from "./billing/viewMeta";

type UserLite = {
  id: number;
  username: string;
  role: string;
};

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const { isMobile } = useResponsive();
const loading = ref(false);
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

const filters = reactive(createBillingFilters());
const customerFilterOptions = computed(() => {
  return [...customers.value].sort((left, right) => left.name.localeCompare(right.name, "zh-CN"));
});

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

const splitAllocatedTotal = computed(() => {
  return splitAllocations.value.reduce((sum, item) => sum + Number(item.allocated_amount || 0), 0);
});

const splitRemainingAmount = computed(() => {
  return Number((splitForm.amount - splitAllocatedTotal.value).toFixed(2));
});

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
    rows.value = [...filteredRows].sort((left, right) => {
      const leftPriority = getDuePriority(left);
      const rightPriority = getDuePriority(right);
      if (leftPriority[0] !== rightPriority[0]) return leftPriority[0] - rightPriority[0];
      if (leftPriority[1] !== rightPriority[1]) return leftPriority[1].localeCompare(rightPriority[1]);
      return leftPriority[2] - rightPriority[2];
    });
  } catch (error) {
    ElMessage.error("获取收费记录失败");
  } finally {
    loading.value = false;
  }
}

async function fetchSummary() {
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
  }
}

async function runBillingQuery() {
  await Promise.all([fetchRecords(), fetchSummary()]);
}

async function fetchCustomers() {
  try {
    const resp = await apiClient.get<CustomerListItem[]>("/customers");
    customers.value = resp.data;
  } catch (error) {
    ElMessage.error("获取客户列表失败");
  }
}

async function fetchAssignableUsers() {
  if (!canManageAssignment.value) return;
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
    path: "/admin/users",
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
  ledgerLoading.value = true;
  try {
    const params: Record<string, string | number> = {
      customer_id: ledgerTargetRecord.value.customer_id,
    };
    if (ledgerDateRange.value?.[0]) {
      params.date_from = ledgerDateRange.value[0];
    }
    if (ledgerDateRange.value?.[1]) {
      params.date_to = ledgerDateRange.value[1];
    }
    const resp = await apiClient.get<BillingLedgerData>("/billing-records/ledger", { params });
    ledgerData.value = resp.data;
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "加载客户明细账失败");
    ledgerData.value = null;
  } finally {
    ledgerLoading.value = false;
  }
}

function openReceiptReconciliation() {
  router.push({
    path: "/receipt-reconciliation",
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

async function submitActivity() {
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
  try {
    await apiClient.post(`/billing-records/${selectedRecord.value.id}/activities`, payload);
    ElMessage.success("记录已保存");
    resetActivityForm();
    await fetchActivities();
    await fetchRecords();
    await fetchSummary();
  } catch (error) {
    ElMessage.error("保存失败");
  }
}

onMounted(async () => {
  await runBillingQuery();
  await fetchCustomers();
  await fetchAssignableUsers();
  await handleRouteAction();
});

watch(
  () => route.fullPath,
  () => {
    void handleRouteAction();
  },
);
</script>

<template>
  <el-space direction="vertical" fill :size="12">
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
    @activity-type-change="onActivityTypeChange"
    @submit="submitActivity"
  />
</template>
