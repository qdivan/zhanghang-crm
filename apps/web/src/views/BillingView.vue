<script setup lang="ts">
import { QuestionFilled } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { apiClient } from "../api/client";
import { useAuthStore } from "../stores/auth";
import type {
  BillingActivity,
  BillingAssignmentItem,
  BillingExecutionLogItem,
  BillingLedgerData,
  BillingPaymentSuggestion,
  BillingRecord,
  CustomerListItem,
} from "../types";
import { commitDateInput } from "../utils/dateInput";
import { todayInBrowserTimeZone } from "../utils/time";

type BillingCreateForm = {
  serial_no: number | null;
  customer_id: number | null;
  charge_category: string;
  charge_mode: "PERIODIC" | "ONE_TIME";
  amount_basis: "MONTHLY" | "YEARLY" | "ONE_TIME" | "PERIOD_TOTAL";
  summary: string;
  total_fee: number;
  monthly_fee: number;
  billing_cycle_text: string;
  period_start_month: string;
  period_end_month: string;
  collection_start_date: string;
  due_month: string;
  payment_method: string;
  status: "CLEARED" | "FULL_ARREARS" | "PARTIAL";
  received_amount: number;
  note: string;
  extra_note: string;
  color_tag: string;
};

type ActivityForm = {
  activity_type: "REMINDER" | "PAYMENT";
  occurred_at: string;
  amount: number;
  payment_nature: "" | "MONTHLY" | "YEARLY" | "ONE_OFF";
  is_prepay: boolean;
  is_settlement: boolean;
  content: string;
  next_followup_at: string | null;
  note: string;
};

type UserLite = {
  id: number;
  username: string;
  role: string;
};

type AssignmentForm = {
  assignee_user_id: number | null;
  assignment_role: "REGISTRATION" | "DELIVERY" | "OTHER";
  note: string;
};

type ExecutionLogForm = {
  occurred_at: string;
  progress_type: "UPDATE" | "MILESTONE" | "BLOCKER" | "DONE";
  content: string;
  next_action: string;
  due_date: string | null;
  note: string;
};

type SplitPaymentForm = {
  occurred_at: string;
  amount: number;
  strategy: "DUE_DATE_ASC" | "SERIAL_ASC" | "AMOUNT_DESC";
  note: string;
};

type SplitAllocationRow = {
  billing_record_id: number;
  serial_no: number;
  summary: string;
  due_month: string;
  outstanding_amount: number;
  allocated_amount: number;
};

type TerminateForm = {
  terminated_at: string;
  reduced_fee: number;
  reason: string;
};

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const loading = ref(false);
const rows = ref<BillingRecord[]>([]);
const customers = ref<CustomerListItem[]>([]);
const summary = ref({
  total_records: 0,
  total_fee: 0,
  total_monthly_fee: 0,
  payment_method_distribution: [] as Array<{ payment_method: string; count: number }>,
  status_distribution: [] as Array<{ status: string; count: number }>,
});

const filters = reactive({
  keyword: "",
  contact_name: "",
  payment_method: "",
  status: "",
});

const showCreateDialog = ref(false);
const createForm = reactive<BillingCreateForm>({
  serial_no: null,
  customer_id: null,
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
});

const paymentMethodOptions = [
  { value: "预收", label: "预收" },
  { value: "后收", label: "后收" },
];

const chargeCategoryOptions = [
  "注册",
  "代账",
  "代账并退税",
  "单独退税",
  "咨询",
  "课程",
  "海外注册",
  "其他",
];

const chargeModeOptions = [
  { value: "PERIODIC", label: "按期" },
  { value: "ONE_TIME", label: "按次" },
];

const amountBasisOptions = [
  { value: "MONTHLY", label: "月费" },
  { value: "YEARLY", label: "年费" },
  { value: "PERIOD_TOTAL", label: "周期总价" },
  { value: "ONE_TIME", label: "单次费用" },
];

const billingStatusOptions = [
  { value: "CLEARED", label: "清账" },
  { value: "PARTIAL", label: "部分收费" },
  { value: "FULL_ARREARS", label: "全欠" },
];

const billingCycleOptions = [
  "按月（每月收）",
  "按季（每3个月收）",
  "半年（每6个月收）",
  "全年（每12个月收）",
  "一次性（单次服务）",
  "自定义周期（见备注）",
];

function normalizePaymentMethod(value: string): "预收" | "后收" {
  return value === "预收" ? "预收" : "后收";
}

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
const activityForm = reactive<ActivityForm>({
  activity_type: "REMINDER",
  occurred_at: todayInBrowserTimeZone(),
  amount: 0,
  payment_nature: "",
  is_prepay: false,
  is_settlement: false,
  content: "",
  next_followup_at: null,
  note: "",
});

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

function normalizeActivityType(value: unknown): "REMINDER" | "PAYMENT" {
  const token = readActivityTypeToken(value);
  const upper = token.toUpperCase();
  if (upper === "PAYMENT" || token.includes("收款")) {
    return "PAYMENT";
  }
  return "REMINDER";
}

function isPaymentActivityType(value: unknown): boolean {
  const token = readActivityTypeToken(value);
  const upper = token.toUpperCase();
  if (!token) return false;
  if (upper === "REMINDER" || token.includes("催收")) return false;
  if (upper === "PAYMENT" || token.includes("收款")) return true;
  // 未识别值时优先放开输入，避免“已选收款但金额无法填写”的阻塞
  return true;
}

const isPaymentActivity = computed(() => isPaymentActivityType(activityForm.activity_type));
const canManageGrant = computed(() => auth.user?.role === "OWNER" || auth.user?.role === "ADMIN");
const canManageAssignment = computed(() => auth.user?.role === "OWNER" || auth.user?.role === "ADMIN");
const showAssignmentDialog = ref(false);
const assignmentLoading = ref(false);
const assignmentSubmitting = ref(false);
const assignmentRows = ref<BillingAssignmentItem[]>([]);
const assignmentTargetRecord = ref<BillingRecord | null>(null);
const assignableUsers = ref<UserLite[]>([]);
const assignmentForm = reactive<AssignmentForm>({
  assignee_user_id: null,
  assignment_role: "DELIVERY",
  note: "",
});
const showExecutionDrawer = ref(false);
const executionLoading = ref(false);
const executionSubmitting = ref(false);
const executionRows = ref<BillingExecutionLogItem[]>([]);
const executionTargetRecord = ref<BillingRecord | null>(null);
const executionForm = reactive<ExecutionLogForm>({
  occurred_at: todayInBrowserTimeZone(),
  progress_type: "UPDATE",
  content: "",
  next_action: "",
  due_date: null,
  note: "",
});
const showSplitPaymentDialog = ref(false);
const splitSuggestionLoading = ref(false);
const splitSubmitting = ref(false);
const splitTargetRecord = ref<BillingRecord | null>(null);
const splitCustomerRecordCount = ref(0);
const splitAllocations = ref<SplitAllocationRow[]>([]);
const splitForm = reactive<SplitPaymentForm>({
  occurred_at: todayInBrowserTimeZone(),
  amount: 0,
  strategy: "DUE_DATE_ASC",
  note: "",
});
const canManageBillingLifecycle = computed(() => auth.user?.role === "OWNER" || auth.user?.role === "ADMIN");
const showTerminateDialog = ref(false);
const terminating = ref(false);
const terminateTargetRecord = ref<BillingRecord | null>(null);
const terminateForm = reactive<TerminateForm>({
  terminated_at: todayInBrowserTimeZone(),
  reduced_fee: 0,
  reason: "",
});
const showLedgerDialog = ref(false);
const ledgerLoading = ref(false);
const ledgerTargetRecord = ref<BillingRecord | null>(null);
const ledgerDateRange = ref<[string, string] | null>(null);
const ledgerData = ref<BillingLedgerData | null>(null);
const ledgerHasDateFilter = computed(() => {
  return Boolean(ledgerDateRange.value?.[0] || ledgerDateRange.value?.[1]);
});
const routeActionHandling = ref(false);

const assignmentRoleOptions = [
  { value: "REGISTRATION", label: "注册办理" },
  { value: "DELIVERY", label: "交付执行" },
  { value: "OTHER", label: "其他支持" },
] as const;

const progressTypeOptions = [
  { value: "UPDATE", label: "进展更新" },
  { value: "MILESTONE", label: "里程碑" },
  { value: "BLOCKER", label: "阻塞问题" },
  { value: "DONE", label: "执行完成" },
] as const;

const paymentStrategyOptions = [
  { value: "DUE_DATE_ASC", label: "到期优先（默认）" },
  { value: "SERIAL_ASC", label: "序号优先" },
  { value: "AMOUNT_DESC", label: "大额优先" },
] as const;

function statusLabel(status: string) {
  if (status === "CLEARED") return "清账";
  if (status === "FULL_ARREARS") return "全欠";
  return "部分收费";
}

function statusTagType(status: string) {
  if (status === "CLEARED") return "success";
  if (status === "FULL_ARREARS") return "danger";
  return "warning";
}

function activityTypeLabel(type: string) {
  return type === "PAYMENT" ? "收款" : "催收";
}

function assignmentRoleLabel(role: string) {
  if (role === "REGISTRATION") return "注册办理";
  if (role === "DELIVERY") return "交付执行";
  return "其他支持";
}

function progressTypeLabel(type: string) {
  if (type === "MILESTONE") return "里程碑";
  if (type === "BLOCKER") return "阻塞问题";
  if (type === "DONE") return "执行完成";
  return "进展更新";
}

function progressTypeTagType(type: string) {
  if (type === "MILESTONE") return "success";
  if (type === "BLOCKER") return "danger";
  if (type === "DONE") return "primary";
  return "info";
}

function ledgerSourceLabel(sourceType: string) {
  return sourceType === "PAYMENT" ? "实收" : "应收";
}

function getMonthDateRange(monthText: string): [string, string] | null {
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

const splitAllocatedTotal = computed(() => {
  return splitAllocations.value.reduce((sum, item) => sum + Number(item.allocated_amount || 0), 0);
});

const splitRemainingAmount = computed(() => {
  return Number((splitForm.amount - splitAllocatedTotal.value).toFixed(2));
});

function shiftMonth(monthText: string, delta: number): string {
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

function applyCreateModeDefaults() {
  if (createForm.charge_mode === "ONE_TIME") {
    createForm.amount_basis = "ONE_TIME";
    createForm.period_start_month = "";
    createForm.period_end_month = "";
    if (!createForm.due_month) {
      createForm.due_month = todayInBrowserTimeZone();
    }
  } else {
    if (createForm.amount_basis === "ONE_TIME") {
      createForm.amount_basis = "MONTHLY";
    }
    if (createForm.period_start_month && !createForm.period_end_month) {
      createForm.period_end_month = shiftMonth(createForm.period_start_month, 11);
    }
  }
}

function onCreateChargeModeChange() {
  applyCreateModeDefaults();
}

function onCreatePeriodStartMonthChange() {
  if (createForm.charge_mode === "PERIODIC" && createForm.period_start_month) {
    createForm.period_end_month = shiftMonth(createForm.period_start_month, 11);
    createForm.collection_start_date = `${createForm.period_start_month}-01`;
  }
}

function syncCreateDerivedDates() {
  applyCreateModeDefaults();
  if (createForm.charge_mode === "PERIODIC") {
    if (createForm.period_start_month && !createForm.collection_start_date) {
      createForm.collection_start_date = `${createForm.period_start_month}-01`;
    }
    if (createForm.period_end_month && !createForm.due_month) {
      createForm.due_month = `${createForm.period_end_month}-28`;
    }
  } else if (!createForm.collection_start_date) {
    createForm.collection_start_date = createForm.due_month || todayInBrowserTimeZone();
  }
}

function canWriteBillingRecord(record: BillingRecord): boolean {
  if (auth.user?.role !== "ACCOUNTANT") return true;
  return record.accountant_username === auth.user.username;
}

async function fetchRecords() {
  loading.value = true;
  try {
    const resp = await apiClient.get<BillingRecord[]>("/billing-records", {
      params: {
        keyword: filters.keyword || undefined,
        contact_name: filters.contact_name || undefined,
      },
    });
    let filteredRows = resp.data;
    if (filters.payment_method) {
      filteredRows = filteredRows.filter((item) => normalizePaymentMethod(item.payment_method) === filters.payment_method);
    }
    if (filters.status) {
      filteredRows = filteredRows.filter((item) => item.status === filters.status);
    }
    rows.value = filteredRows;
  } catch (error) {
    ElMessage.error("获取收费记录失败");
  } finally {
    loading.value = false;
  }
}

async function fetchSummary() {
  try {
    const resp = await apiClient.get("/billing-records/summary");
    summary.value = resp.data;
  } catch (error) {
    ElMessage.error("获取收费统计失败");
  }
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
  if (!createForm.customer_id) {
    ElMessage.warning("请先选择客户");
    return;
  }
  syncCreateDerivedDates();
  try {
    await apiClient.post("/billing-records", createForm);
    ElMessage.success("收费记录已创建");
    showCreateDialog.value = false;
    resetCreateForm();
    await fetchRecords();
    await fetchSummary();
  } catch (error) {
    ElMessage.error("创建失败（需老板/管理员账号）");
  }
}

function resetCreateForm() {
  createForm.serial_no = null;
  createForm.customer_id = null;
  createForm.charge_category = "代账";
  createForm.charge_mode = "PERIODIC";
  createForm.amount_basis = "MONTHLY";
  createForm.summary = "";
  createForm.total_fee = 0;
  createForm.monthly_fee = 0;
  createForm.billing_cycle_text = "按月（每月收）";
  createForm.period_start_month = "";
  createForm.period_end_month = "";
  createForm.collection_start_date = "";
  createForm.due_month = "";
  createForm.payment_method = "预收";
  createForm.status = "PARTIAL";
  createForm.received_amount = 0;
  createForm.note = "";
  createForm.extra_note = "";
  createForm.color_tag = "";
  applyCreateModeDefaults();
}

function openCreateDialog() {
  resetCreateForm();
  showCreateDialog.value = true;
}

function openCustomerDetail(record: BillingRecord) {
  if (!record.customer_id) {
    ElMessage.warning("该收费记录未关联客户档案，请先在收费记录里选择客户");
    return;
  }
  router.push(`/customers/${record.customer_id}`);
}

function openGrantSettings() {
  router.push({
    path: "/admin/users",
    query: { tab: "grants" },
  });
}

function resetAssignmentForm() {
  assignmentForm.assignee_user_id = null;
  assignmentForm.assignment_role = "DELIVERY";
  assignmentForm.note = "";
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
  splitForm.occurred_at = todayInBrowserTimeZone();
  splitForm.amount = 0;
  splitForm.strategy = "DUE_DATE_ASC";
  splitForm.note = "";
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

function normalizeSplitAllocationValue(row: SplitAllocationRow) {
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

  splitSubmitting.value = true;
  try {
    await apiClient.post("/billing-records/payments", {
      customer_id: splitTargetRecord.value.customer_id,
      occurred_at: splitForm.occurred_at,
      amount: splitForm.amount,
      strategy: splitForm.strategy,
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

async function renewBillingRecord(row: BillingRecord) {
  try {
    await ElMessageBox.confirm(
      `确认基于序号 ${row.serial_no} 复制一条续费记录并默认顺延 +1 年？`,
      "确认续费",
      {
        type: "warning",
        confirmButtonText: "确认续费",
        cancelButtonText: "取消",
      },
    );
    await apiClient.post(`/billing-records/${row.id}/renew`, { note: "续费复制生成" });
    ElMessage.success("续费记录已生成");
    await fetchRecords();
    await fetchSummary();
  } catch (error: any) {
    if (error === "cancel") return;
    ElMessage.error(error?.response?.data?.detail ?? "续费失败");
  }
}

function openTerminateDialog(row: BillingRecord) {
  terminateTargetRecord.value = row;
  terminateForm.terminated_at = todayInBrowserTimeZone();
  terminateForm.reduced_fee = 0;
  terminateForm.reason = "提前终止合同";
  showTerminateDialog.value = true;
}

async function submitTerminate() {
  if (!terminateTargetRecord.value) return;
  terminating.value = true;
  try {
    await apiClient.post(`/billing-records/${terminateTargetRecord.value.id}/terminate`, {
      terminated_at: terminateForm.terminated_at,
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

async function openLedgerDialog(row: BillingRecord) {
  if (!row.customer_id) {
    ElMessage.warning("该收费记录缺少客户信息，无法查看明细账");
    return;
  }
  ledgerTargetRecord.value = row;
  ledgerDateRange.value = null;
  ledgerData.value = null;
  showLedgerDialog.value = true;
  await fetchLedgerData();
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
      await renewBillingRecord(target);
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
  executionForm.occurred_at = todayInBrowserTimeZone();
  executionForm.progress_type = "UPDATE";
  executionForm.content = "";
  executionForm.next_action = "";
  executionForm.due_date = null;
  executionForm.note = "";
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
  activityForm.activity_type = "REMINDER";
  activityForm.occurred_at = todayInBrowserTimeZone();
  activityForm.amount = 0;
  activityForm.payment_nature = "";
  activityForm.is_prepay = false;
  activityForm.is_settlement = false;
  activityForm.content = "";
  activityForm.next_followup_at = null;
  activityForm.note = "";
}

function onActivityTypeChange(value: unknown) {
  const paymentMode = isPaymentActivityType(value);
  activityForm.activity_type = paymentMode ? "PAYMENT" : "REMINDER";
  if (!paymentMode) {
    activityForm.amount = 0;
    activityForm.payment_nature = "";
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
  const payload =
    paymentMode
      ? { ...activityForm, activity_type: "PAYMENT" as const }
      : {
          ...activityForm,
          activity_type: "REMINDER" as const,
          amount: 0,
          payment_nature: "",
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
  await fetchRecords();
  await fetchSummary();
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
    <el-row :gutter="12">
      <el-col :xs="24" :md="8">
        <el-card shadow="never">
          <el-statistic title="记录数" :value="summary.total_records" />
        </el-card>
      </el-col>
      <el-col :xs="24" :md="8">
        <el-card shadow="never">
          <el-statistic title="总费用" :value="summary.total_fee" />
        </el-card>
      </el-col>
      <el-col :xs="24" :md="8">
        <el-card shadow="never">
          <el-statistic title="月费用合计" :value="summary.total_monthly_fee" />
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <el-form inline @submit.prevent="fetchRecords" class="billing-filter-form">
        <el-form-item label="关键词">
          <el-input
            v-model="filters.keyword"
            placeholder="序号/客户/联系人/备注"
            clearable
            @keyup.enter="fetchRecords"
          />
        </el-form-item>
        <el-form-item label="联系人">
          <el-input
            v-model="filters.contact_name"
            placeholder="客户联系人"
            clearable
            @keyup.enter="fetchRecords"
          />
        </el-form-item>
        <el-form-item>
          <template #label>
            <span class="label-with-help">
              付款方式
              <el-tooltip placement="top" :show-after="150">
                <template #content>
                  <div>预收：服务开始前先收费</div>
                  <div>后收：到期日/账期结束后再收费</div>
                </template>
                <el-icon class="help-icon"><QuestionFilled /></el-icon>
              </el-tooltip>
            </span>
          </template>
          <el-select v-model="filters.payment_method" placeholder="全部" clearable>
            <el-option
              v-for="item in paymentMethodOptions"
              :key="`filter-method-${item.value}`"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <template #label>
            <span class="label-with-help">
              台账状态
              <el-tooltip placement="top" :show-after="150">
                <template #content>
                  <div>清账：已收齐，未收金额为 0</div>
                  <div>部分收费：已收部分，仍有未收</div>
                  <div>全欠：尚未收款</div>
                </template>
                <el-icon class="help-icon"><QuestionFilled /></el-icon>
              </el-tooltip>
            </span>
          </template>
          <el-select v-model="filters.status" placeholder="全部" clearable>
            <el-option
              v-for="item in billingStatusOptions"
              :key="`filter-status-${item.value}`"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button @click="fetchRecords">查询</el-button>
          <el-button type="primary" @click="openCreateDialog">新增收费记录</el-button>
          <el-button v-if="canManageGrant" type="primary" plain @click="openGrantSettings">数据授权配置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="head">
          <span>收费台账（对齐 `周 (2)` 结构）</span>
          <el-tag type="success" effect="plain">{{ rows.length }} 条</el-tag>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe border>
        <el-table-column
          prop="serial_no"
          label="序号"
          width="90"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column label="名称" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <el-button link type="primary" @click="openCustomerDetail(row)">
              {{ row.customer_name }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column
          prop="customer_contact_name"
          label="联系人"
          width="110"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="charge_category"
          label="收费类别"
          width="110"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          label="计费"
          width="80"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        >
          <template #default="{ row }">
            {{ row.charge_mode === "ONE_TIME" ? "按次" : "按期" }}
          </template>
        </el-table-column>
        <el-table-column
          label="金额口径"
          width="100"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        >
          <template #default="{ row }">
            {{
              row.amount_basis === "YEARLY"
                ? "年费"
                : row.amount_basis === "PERIOD_TOTAL"
                  ? "周期总价"
                  : row.amount_basis === "ONE_TIME"
                    ? "单次费用"
                    : "月费"
            }}
          </template>
        </el-table-column>
        <el-table-column
          prop="accountant_username"
          label="会计"
          width="100"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="total_fee"
          label="总费用"
          width="90"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="received_amount"
          label="已收"
          width="85"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column prop="outstanding_amount" label="未收" width="80" />
        <el-table-column
          label="状态"
          width="90"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        >
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="monthly_fee"
          label="月费用"
          width="85"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="billing_cycle_text"
          label="代账周期"
          min-width="170"
          show-overflow-tooltip
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="due_month"
          label="到期日"
          width="100"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="summary"
          label="摘要"
          min-width="130"
          show-overflow-tooltip
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="collection_start_date"
          label="起收日期"
          width="108"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          label="付款方式"
          width="110"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        >
          <template #default="{ row }">
            {{ normalizePaymentMethod(row.payment_method) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="note"
          label="备注"
          min-width="160"
          show-overflow-tooltip
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="extra_note"
          label="扩展"
          min-width="120"
          show-overflow-tooltip
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column label="操作" width="560">
          <template #default="{ row }">
            <el-space>
              <el-button link type="info" @click="openLedgerDialog(row)">
                明细账
              </el-button>
              <el-button link type="success" :disabled="!canWriteBillingRecord(row)" @click="openSplitPaymentDialog(row)">
                分摊收款
              </el-button>
              <el-button link type="warning" @click="openExecutionDrawer(row)">
                执行进度
              </el-button>
              <el-button link type="primary" :disabled="!canWriteBillingRecord(row)" @click="openActivityDrawer(row)">
                催收/收款
              </el-button>
              <el-button v-if="canManageAssignment" link type="success" @click="openAssignmentDialog(row)">
                分派执行
              </el-button>
              <el-button
                v-if="canManageBillingLifecycle"
                link
                type="primary"
                @click="renewBillingRecord(row)"
              >
                续费+1年
              </el-button>
              <el-button
                v-if="canManageBillingLifecycle"
                link
                type="danger"
                @click="openTerminateDialog(row)"
              >
                提前终止
              </el-button>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-row :gutter="12">
      <el-col :xs="24" :md="12">
        <el-card shadow="never">
          <template #header>付款方式分布</template>
          <el-space wrap>
            <el-tag
              v-for="item in paymentMethodDistributionNormalized"
              :key="item.payment_method"
              type="info"
              effect="plain"
            >
              {{ item.payment_method }}：{{ item.count }}
            </el-tag>
          </el-space>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card shadow="never">
          <template #header>状态分布</template>
          <el-space wrap>
            <el-tag
              v-for="item in summary.status_distribution"
              :key="item.status"
              :type="statusTagType(item.status)"
              effect="plain"
            >
              {{ statusLabel(item.status) }}：{{ item.count }}
            </el-tag>
          </el-space>
        </el-card>
      </el-col>
    </el-row>
  </el-space>

  <el-dialog v-model="showCreateDialog" title="新增收费记录" width="760px">
    <el-form label-position="top">
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="序号">
            <el-input-number
              v-model="createForm.serial_no"
              :min="1"
              :controls="false"
              style="width:100%"
              placeholder="留空自动编号"
            />
          </el-form-item>
        </el-col>
        <el-col :span="16">
          <el-form-item label="客户">
            <el-select v-model="createForm.customer_id" filterable placeholder="请选择客户">
              <el-option
                v-for="item in customers"
                :key="item.id"
                :label="`${item.name}（${item.contact_name}）`"
                :value="item.id"
              />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="6">
          <el-form-item label="收费类别">
            <el-select v-model="createForm.charge_category">
              <el-option
                v-for="item in chargeCategoryOptions"
                :key="`create-category-${item}`"
                :label="item"
                :value="item"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="计费方式">
            <el-select v-model="createForm.charge_mode" @change="onCreateChargeModeChange">
              <el-option
                v-for="item in chargeModeOptions"
                :key="`create-mode-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="金额口径">
            <el-select v-model="createForm.amount_basis">
              <el-option
                v-for="item in amountBasisOptions"
                :key="`create-basis-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="摘要">
            <el-input v-model="createForm.summary" placeholder="例如：2026年服务费" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="6"><el-form-item label="总费用"><el-input-number v-model="createForm.total_fee" :min="0" :controls="false" style="width:100%" /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="月费用"><el-input-number v-model="createForm.monthly_fee" :min="0" :controls="false" style="width:100%" /></el-form-item></el-col>
        <el-col :span="6">
          <el-form-item label="开始月份">
            <el-date-picker
              v-model="createForm.period_start_month"
              type="month"
              format="YYYY-MM"
              value-format="YYYY-MM"
              :disabled="createForm.charge_mode === 'ONE_TIME'"
              placeholder="YYYY-MM"
              @change="onCreatePeriodStartMonthChange"
            />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="结束月份">
            <el-date-picker
              v-model="createForm.period_end_month"
              type="month"
              format="YYYY-MM"
              value-format="YYYY-MM"
              :disabled="createForm.charge_mode === 'ONE_TIME'"
              placeholder="YYYY-MM"
            />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="6">
          <el-form-item label="起收日期（精确）">
            <el-date-picker
              v-model="createForm.collection_start_date"
              type="date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              :editable="true"
              placeholder="YYYYMMDD 或 YYMMDD"
              @keydown.enter.capture="commitDateInput((v) => (createForm.collection_start_date = v), $event)"
              @blur.capture="commitDateInput((v) => (createForm.collection_start_date = v), $event)"
            />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="到期日">
            <el-date-picker
              v-model="createForm.due_month"
              type="date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              :editable="true"
              placeholder="YYYYMMDD 或 YYMMDD"
              @keydown.enter.capture="commitDateInput((v) => (createForm.due_month = v), $event)"
              @blur.capture="commitDateInput((v) => (createForm.due_month = v), $event)"
            />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-text type="info" size="small">
            {{ createForm.charge_mode === "ONE_TIME" ? "按次：默认当天到期" : "按期：默认结束月份=开始月份+11" }}
          </el-text>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item>
            <template #label>
              <span class="label-with-help">
                付款方式
                <el-tooltip placement="top" :show-after="150">
                  <template #content>
                    <div>预收：服务开始前先收费</div>
                    <div>后收：到期日/账期结束后再收费</div>
                  </template>
                  <el-icon class="help-icon"><QuestionFilled /></el-icon>
                </el-tooltip>
              </span>
            </template>
            <el-select v-model="createForm.payment_method">
              <el-option
                v-for="item in paymentMethodOptions"
                :key="`create-method-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item>
            <template #label>
              <span class="label-with-help">
                台账状态
                <el-tooltip placement="top" :show-after="150">
                  <template #content>
                    <div>清账：已收齐，未收金额为 0</div>
                    <div>部分收费：已收部分，仍有未收</div>
                    <div>全欠：尚未收款</div>
                  </template>
                  <el-icon class="help-icon"><QuestionFilled /></el-icon>
                </el-tooltip>
              </span>
            </template>
            <el-select v-model="createForm.status">
              <el-option
                v-for="item in billingStatusOptions"
                :key="`create-status-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="已收金额"><el-input-number v-model="createForm.received_amount" :min="0" :controls="false" style="width:100%" /></el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="代账周期">
        <el-select v-model="createForm.billing_cycle_text" placeholder="请选择代账周期">
          <el-option
            v-for="item in billingCycleOptions"
            :key="`cycle-${item}`"
            :label="item"
            :value="item"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="createForm.note" type="textarea" :rows="2" />
      </el-form-item>
      <el-form-item label="扩展说明">
        <el-input v-model="createForm.extra_note" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showCreateDialog = false">取消</el-button>
      <el-button type="primary" @click="createRecord">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog
    v-model="showLedgerDialog"
    :title="`客户明细账 - ${ledgerTargetRecord?.customer_name ?? ''}`"
    width="960px"
  >
    <el-form inline>
      <el-form-item label="时间范围">
        <el-date-picker
          v-model="ledgerDateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          format="YYYY-MM-DD"
          unlink-panels
        />
      </el-form-item>
      <el-form-item>
        <el-button :loading="ledgerLoading" @click="fetchLedgerData">查询</el-button>
      </el-form-item>
      <el-form-item>
        <el-button v-if="ledgerHasDateFilter" text @click="resetLedgerDateFilter">查看全部</el-button>
      </el-form-item>
    </el-form>

    <el-row :gutter="12" class="ledger-stats">
      <el-col :span="8">
        <el-card shadow="never">
          <el-statistic title="应收合计" :value="ledgerData?.receivable_total ?? 0" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never">
          <el-statistic title="实收合计" :value="ledgerData?.received_total ?? 0" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never">
          <el-statistic title="余额" :value="ledgerData?.balance ?? 0" />
        </el-card>
      </el-col>
    </el-row>

    <el-divider content-position="left">按月汇总</el-divider>
    <el-table v-loading="ledgerLoading" :data="ledgerData?.monthly_summaries || []" stripe border>
      <el-table-column prop="month" label="月份" width="110" />
      <el-table-column prop="receivable_total" label="当月应收" width="120" />
      <el-table-column prop="received_total" label="当月实收" width="120" />
      <el-table-column prop="net_change" label="净变动(应收-实收)" width="160" />
      <el-table-column prop="ending_balance" label="月末余额" width="120" />
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button link type="primary" @click="drillDownLedgerMonth(row.month)">下钻</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-divider content-position="left">流水明细</el-divider>
    <el-table v-loading="ledgerLoading" :data="ledgerData?.entries || []" stripe border>
      <el-table-column prop="occurred_at" label="时间" width="110" />
      <el-table-column prop="summary" label="摘要" min-width="220" show-overflow-tooltip />
      <el-table-column label="类型" width="90">
        <template #default="{ row }">
          <el-tag :type="row.source_type === 'PAYMENT' ? 'success' : 'info'" size="small">
            {{ ledgerSourceLabel(row.source_type) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="receivable_amount" label="应收" width="110" />
      <el-table-column prop="received_amount" label="实收" width="110" />
      <el-table-column prop="balance" label="余额" width="110" />
    </el-table>
  </el-dialog>

  <el-dialog
    v-model="showSplitPaymentDialog"
    :title="`分摊收款 - ${splitTargetRecord?.customer_name ?? ''}`"
    width="860px"
  >
    <el-form label-position="top">
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="收款日期">
            <el-date-picker
              v-model="splitForm.occurred_at"
              type="date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              :editable="true"
              placeholder="YYYYMMDD 或 YYMMDD"
              @keydown.enter.capture="commitDateInput((v) => (splitForm.occurred_at = v), $event)"
              @blur.capture="commitDateInput((v) => (splitForm.occurred_at = v), $event)"
            />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="收款总额">
            <el-input-number v-model="splitForm.amount" :min="0" :controls="false" style="width:100%" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="优先策略">
            <el-select v-model="splitForm.strategy">
              <el-option
                v-for="item in paymentStrategyOptions"
                :key="`split-strategy-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="收款备注">
        <el-input v-model="splitForm.note" placeholder="例如：客户按整数付款，按约定优先抵扣到期项目" />
      </el-form-item>
      <el-space>
        <el-button :loading="splitSuggestionLoading" @click="buildSplitSuggestions">生成默认分摊建议</el-button>
        <el-text type="info" size="small">
          支持手动改金额；需保证分摊合计 = 收款总额
        </el-text>
      </el-space>
    </el-form>

    <el-divider />

    <el-table v-loading="splitSuggestionLoading" :data="splitAllocations" stripe border>
      <el-table-column prop="serial_no" label="序号" width="80" />
      <el-table-column prop="summary" label="摘要" min-width="180" show-overflow-tooltip />
      <el-table-column prop="due_month" label="到期日" width="110" />
      <el-table-column prop="outstanding_amount" label="当前未收" width="110" />
      <el-table-column label="本次分摊金额" width="170">
        <template #default="{ row }">
          <el-input-number
            v-model="row.allocated_amount"
            :min="0"
            :controls="false"
            style="width:100%"
            @change="normalizeSplitAllocationValue(row)"
          />
        </template>
      </el-table-column>
    </el-table>

    <div class="split-summary">
      <el-text type="info">项目数：{{ splitCustomerRecordCount }}</el-text>
      <el-text type="info">分摊合计：{{ splitAllocatedTotal.toFixed(2) }}</el-text>
      <el-text :type="Math.abs(splitRemainingAmount) < 0.01 ? 'success' : 'danger'">
        待分配：{{ splitRemainingAmount.toFixed(2) }}
      </el-text>
    </div>

    <template #footer>
      <el-button @click="showSplitPaymentDialog = false">取消</el-button>
      <el-button type="primary" :loading="splitSubmitting" @click="submitSplitPayment">确认分摊并入账</el-button>
    </template>
  </el-dialog>

  <el-dialog
    v-model="showTerminateDialog"
    :title="`提前终止合同 - ${terminateTargetRecord?.customer_name ?? ''}`"
    width="560px"
  >
    <el-form label-position="top">
      <el-form-item label="终止日期">
        <el-date-picker
          v-model="terminateForm.terminated_at"
          type="date"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          :editable="true"
          placeholder="YYYYMMDD 或 YYMMDD"
          @keydown.enter.capture="commitDateInput((v) => (terminateForm.terminated_at = v), $event)"
          @blur.capture="commitDateInput((v) => (terminateForm.terminated_at = v), $event)"
        />
      </el-form-item>
      <el-form-item label="冲减费用">
        <el-input-number v-model="terminateForm.reduced_fee" :min="0" :controls="false" style="width:100%" />
      </el-form-item>
      <el-form-item label="终止原因">
        <el-input v-model="terminateForm.reason" type="textarea" :rows="3" />
      </el-form-item>
      <el-text type="info" size="small">
        提交后会更新该收费单的应收总额、到期日和账单状态。
      </el-text>
    </el-form>
    <template #footer>
      <el-button @click="showTerminateDialog = false">取消</el-button>
      <el-button type="danger" :loading="terminating" @click="submitTerminate">确认终止并冲减</el-button>
    </template>
  </el-dialog>

  <el-dialog
    v-model="showAssignmentDialog"
    :title="`执行分派 - ${assignmentTargetRecord?.customer_name ?? ''}`"
    width="760px"
  >
    <el-form label-position="top">
      <el-row :gutter="12">
        <el-col :span="10">
          <el-form-item label="执行人员">
            <el-select v-model="assignmentForm.assignee_user_id" filterable placeholder="请选择执行人员">
              <el-option
                v-for="item in assignableUsers"
                :key="`assign-user-${item.id}`"
                :label="`${item.username}（${item.role}）`"
                :value="item.id"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="分派角色">
            <el-select v-model="assignmentForm.assignment_role">
              <el-option
                v-for="item in assignmentRoleOptions"
                :key="`assignment-role-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="操作">
            <el-button type="primary" :loading="assignmentSubmitting" @click="createAssignment">新增分派</el-button>
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="说明">
        <el-input v-model="assignmentForm.note" placeholder="可选：填写分派说明，例如负责股权变更办理" />
      </el-form-item>
    </el-form>

    <el-divider />

    <el-table v-loading="assignmentLoading" :data="assignmentRows" stripe border>
      <el-table-column prop="assignee_username" label="执行人员" width="130" />
      <el-table-column prop="assignee_role" label="系统角色" width="110" />
      <el-table-column label="分派角色" width="120">
        <template #default="{ row }">
          {{ assignmentRoleLabel(row.assignment_role) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? "生效" : "停用" }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="note" label="说明" min-width="160" show-overflow-tooltip />
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button
            link
            type="danger"
            :disabled="!row.is_active"
            @click="deactivateAssignment(row)"
          >
            取消
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-dialog>

  <el-drawer
    v-model="showExecutionDrawer"
    :title="`执行进度 - ${executionTargetRecord?.customer_name ?? ''}`"
    size="min(820px, 95vw)"
  >
    <el-form label-position="top">
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="进度类型">
            <el-select v-model="executionForm.progress_type">
              <el-option
                v-for="item in progressTypeOptions"
                :key="`progress-type-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="进度日期">
            <el-date-picker
              v-model="executionForm.occurred_at"
              type="date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              :editable="true"
              placeholder="YYYYMMDD 或 YYMMDD"
              @keydown.enter.capture="commitDateInput((v) => (executionForm.occurred_at = v), $event)"
              @blur.capture="commitDateInput((v) => (executionForm.occurred_at = v), $event)"
            />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="目标完成日">
            <el-date-picker
              v-model="executionForm.due_date"
              type="date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              :editable="true"
              placeholder="YYYYMMDD 或 YYMMDD"
              @keydown.enter.capture="commitDateInput((v) => (executionForm.due_date = v), $event)"
              @blur.capture="commitDateInput((v) => (executionForm.due_date = v), $event)"
            />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="进度内容">
        <el-input v-model="executionForm.content" type="textarea" :rows="3" />
      </el-form-item>
      <el-form-item label="下一步动作">
        <el-input v-model="executionForm.next_action" placeholder="例如：等待客户回传材料、预约办理时间" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="executionForm.note" />
      </el-form-item>
      <el-button type="primary" :loading="executionSubmitting" @click="submitExecutionLog">保存进度</el-button>
    </el-form>

    <el-divider />

    <el-table v-loading="executionLoading" :data="executionRows" stripe border>
      <el-table-column prop="occurred_at" label="日期" width="110" />
      <el-table-column label="类型" width="100">
        <template #default="{ row }">
          <el-tag :type="progressTypeTagType(row.progress_type)" size="small">
            {{ progressTypeLabel(row.progress_type) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="content" label="进度内容" min-width="220" show-overflow-tooltip />
      <el-table-column prop="next_action" label="下一步" min-width="180" show-overflow-tooltip />
      <el-table-column prop="due_date" label="目标完成" width="110" />
      <el-table-column prop="actor_username" label="记录人" width="100" />
      <el-table-column prop="note" label="备注" min-width="130" show-overflow-tooltip />
    </el-table>
  </el-drawer>

  <el-drawer
    v-model="showActivityDrawer"
    :title="`催收/收款 - ${selectedRecord?.customer_name ?? ''}`"
    size="min(760px, 92vw)"
  >
    <el-form label-position="top">
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="类型">
            <el-select v-model="activityForm.activity_type" @change="onActivityTypeChange">
              <el-option label="催收" value="REMINDER" />
              <el-option label="收款" value="PAYMENT" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="日期">
            <el-date-picker
              v-model="activityForm.occurred_at"
              type="date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              :editable="true"
              placeholder="YYYYMMDD 或 YYMMDD"
              @keydown.enter.capture="commitDateInput((v) => (activityForm.occurred_at = v), $event)"
              @blur.capture="commitDateInput((v) => (activityForm.occurred_at = v), $event)"
            />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="金额（收款时）">
            <el-input-number
              v-model="activityForm.amount"
              :min="0"
              :controls="false"
              style="width:100%"
            />
            <el-text v-if="!isPaymentActivity" type="info" size="small">
              当前为催收，保存时金额会自动记为 0
            </el-text>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="收款类型">
            <el-select v-model="activityForm.payment_nature" clearable :disabled="!isPaymentActivity">
              <el-option label="月付" value="MONTHLY" />
              <el-option label="年付" value="YEARLY" />
              <el-option label="一次性" value="ONE_OFF" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="下次跟进">
            <el-date-picker
              v-model="activityForm.next_followup_at"
              type="date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              :editable="true"
              placeholder="YYYYMMDD 或 YYMMDD"
              @keydown.enter.capture="commitDateInput((v) => (activityForm.next_followup_at = v), $event)"
              @blur.capture="commitDateInput((v) => (activityForm.next_followup_at = v), $event)"
            />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="结算标记">
            <el-space>
              <el-checkbox v-model="activityForm.is_prepay" :disabled="!isPaymentActivity">
                预付
              </el-checkbox>
              <el-checkbox v-model="activityForm.is_settlement" :disabled="!isPaymentActivity">
                结清
              </el-checkbox>
            </el-space>
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="内容">
        <el-input v-model="activityForm.content" type="textarea" :rows="3" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="activityForm.note" />
      </el-form-item>
      <el-button type="primary" @click="submitActivity">保存日志</el-button>
    </el-form>

    <el-divider />

    <el-table v-loading="activityLoading" :data="activityRows" stripe border>
      <el-table-column prop="occurred_at" label="日期" width="120" />
      <el-table-column label="类型" width="80">
        <template #default="{ row }">
          <el-tag size="small" :type="row.activity_type === 'PAYMENT' ? 'success' : 'warning'">
            {{ activityTypeLabel(row.activity_type) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="amount" label="金额" width="90" />
      <el-table-column
        prop="payment_nature"
        label="性质"
        width="90"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column prop="content" label="内容" min-width="180" show-overflow-tooltip />
      <el-table-column
        prop="next_followup_at"
        label="下次跟进"
        width="120"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        prop="note"
        label="备注"
        min-width="130"
        show-overflow-tooltip
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
    </el-table>
  </el-drawer>
</template>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.label-with-help {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.help-icon {
  color: #909399;
  font-size: 14px;
  cursor: help;
}

.split-summary {
  margin-top: 10px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 14px;
}

.ledger-stats {
  margin-bottom: 12px;
}

@media (max-width: 900px) {
  .billing-filter-form {
    display: flex;
    flex-wrap: wrap;
  }
}
</style>
