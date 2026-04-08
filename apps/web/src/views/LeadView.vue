<script setup lang="ts">
import { Filter, MoreFilled } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { apiClient } from "../api/client";
import MobileActionSheet from "../components/mobile/MobileActionSheet.vue";
import MobileFilterSheet from "../components/mobile/MobileFilterSheet.vue";
import LeadConvertBillingDialog from "../components/leads/LeadConvertBillingDialog.vue";
import LeadConvertDialog from "../components/leads/LeadConvertDialog.vue";
import LeadCreateDialog from "../components/leads/LeadCreateDialog.vue";
import LeadFilterCard from "../components/leads/LeadFilterCard.vue";
import LeadFollowupDialog from "../components/leads/LeadFollowupDialog.vue";
import LeadGuideDialog from "../components/leads/LeadGuideDialog.vue";
import LeadHistoryDrawer from "../components/leads/LeadHistoryDrawer.vue";
import LeadOverviewCard from "../components/leads/LeadOverviewCard.vue";
import LeadRedevelopDialog from "../components/leads/LeadRedevelopDialog.vue";
import { useMobileFilterMemory } from "../composables/useMobileFilterMemory";
import { isMobileAppPath } from "../mobile/config";
import { useAuthStore } from "../stores/auth";
import type { BillingCreatePayload, BillingRecord, LeadItem } from "../types";
import {
  createEmptyBillingDraft,
  prepareBillingDraftsForSubmit,
  validateBillingDraft,
} from "../utils/billingDraft";
import { todayInBrowserTimeZone } from "../utils/time";
import {
  createLeadConvertForm,
  createLeadFilters,
  createLeadFollowupForm,
  createLeadForm,
  createLeadRedevelopForm,
  type LeadConvertForm,
  type LeadCreateForm,
  type LeadFollowupForm,
  type LeadRedevelopForm,
} from "./lead/forms";
import {
  findExactLeadCustomer,
  searchLeadCustomers,
  type LeadCustomerSearchItem,
} from "./lead/customerSearch";
import {
  getDefaultReminderValueForGrade,
  getLeadAreaText,
  getLeadContactText,
  getLeadStartText,
  getStatusLabel,
  getTemplateLabel,
  statusTagType,
} from "./lead/viewMeta";

type FollowupItem = {
  id: number;
  lead_id: number;
  followup_at: string;
  feedback: string;
  next_reminder_at: string | null;
  notes: string;
  created_by: number;
  created_by_username: string;
  created_at: string;
};

type UserLite = {
  id: number;
  username: string;
  role: string;
};

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const loading = ref(false);
const leadsHydrated = ref(false);
const rows = ref<LeadItem[]>([]);
const showLeadDialog = ref(false);
const showRedevelopDialog = ref(false);
const showFollowupDialog = ref(false);
const showHistoryDrawer = ref(false);
const showConvertDialog = ref(false);
const showConvertBillingDialog = ref(false);
const showGuideDialog = ref(false);
const historyLoading = ref(false);
const historyRows = ref<FollowupItem[]>([]);
const historyLeadName = ref("");
const convertTargetLeadName = ref("");
const convertBillingTargetName = ref("");
const userOptions = ref<UserLite[]>([]);
const accountantOptions = ref<UserLite[]>([]);
const converting = ref(false);
const creatingConvertBilling = ref(false);
const creatingRedevelopLead = ref(false);
const redevelopSearchLoading = ref(false);
const redevelopCustomerOptions = ref<LeadCustomerSearchItem[]>([]);
const redevelopForm = reactive<LeadRedevelopForm>(createLeadRedevelopForm());
const convertForm = reactive<LeadConvertForm>(createLeadConvertForm());
const convertBillingRows = ref<BillingCreatePayload[]>([createEmptyBillingDraft(null)]);
const showMobileFilters = ref(false);
const expandedLeadId = ref<number | null>(null);
const showLeadPageActionSheet = ref(false);
const showLeadRowActionSheet = ref(false);
const selectedLeadActionRow = ref<LeadItem | null>(null);
const leadRouteQueueHandling = ref(false);

const filters = reactive(createLeadFilters());
const leadMobileFilterMemory = useMobileFilterMemory("crm.mobile_filters.leads", createLeadFilters());
const leadForm = reactive<LeadCreateForm>(createLeadForm());
const followupForm = reactive<LeadFollowupForm>(createLeadFollowupForm(todayInBrowserTimeZone()));

const canConvert = computed(
  () => auth.user?.role === "OWNER" || auth.user?.role === "MANAGER",
);
const canDeleteLead = computed(() => auth.user?.role === "OWNER" || auth.user?.role === "ADMIN");
const isMobileWorkflow = computed(() => isMobileAppPath(route.path));
const leadFilterChips = computed(() =>
  [
    filters.keyword ? { key: "keyword", label: `关键词：${filters.keyword}` } : null,
    filters.status ? { key: "status", label: `状态：${getStatusLabel(filters.status as LeadItem["status"])}` } : null,
    filters.template_type
      ? { key: "template_type", label: `模板：${getTemplateLabel(filters.template_type as LeadItem["template_type"])}` }
      : null,
  ].filter(Boolean) as Array<{ key: "keyword" | "status" | "template_type"; label: string }>,
);
const activeFilterChips = computed(() => leadFilterChips.value.map((item) => item.label));
const mobileFollowupQueueLabel = computed(() => {
  const currentIndex = rows.value.findIndex((item) => item.id === followupForm.lead_id);
  if (currentIndex < 0) return "";
  return `${currentIndex + 1} / ${rows.value.length}`;
});
const hasNextFollowupLead = computed(() => {
  const currentIndex = rows.value.findIndex((item) => item.id === followupForm.lead_id);
  return currentIndex >= 0 && currentIndex < rows.value.length - 1;
});
const leadQuickFilters = computed(() => [
  { key: "all" as const, label: "全部", active: !filters.status && !filters.template_type },
  { key: "following" as const, label: "跟进中", active: filters.status === "FOLLOWING" && !filters.template_type },
  { key: "new" as const, label: "新线索", active: filters.status === "NEW" && !filters.template_type },
  { key: "redevelop" as const, label: "老客二开", active: !filters.status && filters.template_type === "REDEVELOP" },
]);
const leadPageActionItems = computed(() => [
  { key: "redevelop", label: "老客二次开发", description: "快速基于老客户补一条二开线索。" },
  { key: "guide", label: "流程说明", description: "查看开发流程和字段使用说明。" },
  { key: "import", label: "导入 Excel", description: "保留导入入口，后续继续接入。", disabled: true },
]);
const showLeadInitialSkeleton = computed(() => !leadsHydrated.value);
const leadSortBy = ref(String(route.query.sort_by || "id"));
const leadSortOrder = ref<"asc" | "desc">(route.query.sort_order === "asc" ? "asc" : "desc");
const leadRowActionItems = computed(() => {
  const row = selectedLeadActionRow.value;
  if (!row) return [];
  return [
    { key: "detail", label: "查看详情", description: "进入完整线索详情页。" },
    { key: "history", label: "跟进历史", description: "查看这条线索的全部跟进记录。" },
    row.customer_id
      ? { key: "customer", label: "客户档案", description: "跳转到已转化的客户档案。" }
      : {
          key: "convert",
          label: "转化成交",
          description: canConvert.value ? "将这条线索转为客户并分配负责人员。" : "当前账号没有转化权限。",
          disabled: !canConvert.value || row.status === "CONVERTED",
        },
    row.status === "CONVERTED"
      ? {
          key: "revoke",
          label: "撤销转化",
          description: canConvert.value ? "撤回已转化的客户档案。" : "当前账号没有撤销权限。",
          danger: true,
          disabled: !canConvert.value,
        }
      : null,
    canDeleteLead.value
      ? {
          key: "delete",
          label: "删除线索",
          description:
            row.status === "CONVERTED" ? "已转化线索需先撤销转化后再删除。" : "删除后会移除这条线索记录。",
          danger: true,
        }
      : null,
  ].filter(Boolean) as Array<{ key: string; label: string; description: string; disabled?: boolean; danger?: boolean }>;
});

function currentLeadFilterSnapshot() {
  return {
    keyword: filters.keyword,
    status: filters.status,
    template_type: filters.template_type,
  };
}

function leadSortOrderForTable() {
  return leadSortOrder.value === "asc" ? "ascending" : "descending";
}

async function applyLeadSort(sortBy: string, sortOrder: "asc" | "desc") {
  leadSortBy.value = sortBy;
  leadSortOrder.value = sortOrder;
  await router.replace({
    path: route.path,
    query: {
      ...route.query,
      sort_by: sortBy,
      sort_order: sortOrder,
    },
  });
  await fetchLeads();
}

async function handleLeadSortChange(payload: { prop?: string; order: "ascending" | "descending" | null; columnKey?: string }) {
  const sortKey = payload.columnKey || payload.prop || "id";
  const sortOrder = payload.order === "ascending" ? "asc" : "desc";
  await applyLeadSort(sortKey, sortOrder);
}

async function fetchLeads() {
  loading.value = true;
  try {
    const resp = await apiClient.get<LeadItem[]>("/leads", {
      params: {
        keyword: filters.keyword || undefined,
        status: filters.status || undefined,
        sort_by: leadSortBy.value || "id",
        sort_order: leadSortOrder.value || "desc",
      },
    });
    const activeLeadRows = resp.data.filter((item) => item.status !== "CONVERTED");
    const filtered = filters.template_type
      ? activeLeadRows.filter((item) => item.template_type === filters.template_type)
      : activeLeadRows;
    rows.value = filtered;
  } catch (error) {
    ElMessage.error("获取线索失败");
  } finally {
    loading.value = false;
    leadsHydrated.value = true;
  }
}

async function createLead() {
  if (!leadForm.contact_name.trim()) {
    ElMessage.warning("请填写联系人");
    return;
  }
  if (leadForm.template_type !== "FOLLOWUP" && !leadForm.contact_start_date) {
    ElMessage.warning("请填写联络开始时间");
    return;
  }
  if (!leadForm.main_business.trim()) {
    ElMessage.warning("请填写主营/需要");
    return;
  }
  if (!leadForm.source.trim()) {
    ElMessage.warning("请填写来源");
    return;
  }

  try {
    const rawCompanyName = leadForm.name.trim();
    const effectiveCompanyName = rawCompanyName || leadForm.contact_name.trim();
    const payload = {
      ...leadForm,
      name: effectiveCompanyName,
      contact_name: leadForm.contact_name.trim(),
      main_business: leadForm.main_business.trim(),
      intro: leadForm.intro.trim(),
      source: leadForm.source.trim(),
      phone: leadForm.phone.trim(),
    };

    let autoLinkedCustomerName = "";
    if (!leadForm.related_customer_id && rawCompanyName) {
      const exactCustomer = await findExactLeadCustomer(rawCompanyName);
      if (exactCustomer) {
        payload.related_customer_id = exactCustomer.id;
        autoLinkedCustomerName = exactCustomer.name;
      }
    }

    await apiClient.post("/leads", payload);
    ElMessage.success(
      autoLinkedCustomerName
        ? `线索已创建，已自动关联现有客户：${autoLinkedCustomerName}`
        : "线索已创建",
    );
    showLeadDialog.value = false;
    resetLeadForm();
    await fetchLeads();
  } catch (error) {
    ElMessage.error("创建线索失败");
  }
}

async function fetchUserOptions() {
  if (!canConvert.value) {
    userOptions.value = [];
    accountantOptions.value = [];
    return;
  }
  try {
    const [usersResp, accountantsResp] = await Promise.all([
      apiClient.get<UserLite[]>("/users", {
        params: { scope: "all_active" },
      }),
      apiClient.get<UserLite[]>("/users", {
        params: { role: "ACCOUNTANT", scope: "all_active" },
      }),
    ]);
    userOptions.value = usersResp.data;
    accountantOptions.value = accountantsResp.data;
  } catch (error) {
    ElMessage.error("获取负责人员列表失败");
  }
}

async function ensureAccountantsLoaded() {
  if (!canConvert.value || (accountantOptions.value.length && userOptions.value.length)) return;
  await fetchUserOptions();
}

function resetRedevelopForm() {
  Object.assign(redevelopForm, createLeadRedevelopForm());
  redevelopCustomerOptions.value = [];
}

function openRedevelopDialog() {
  resetRedevelopForm();
  showRedevelopDialog.value = true;
}

async function searchRedevelopCustomers(keyword: string) {
  const q = keyword.trim();
  if (!q) {
    redevelopCustomerOptions.value = [];
    return;
  }
  redevelopSearchLoading.value = true;
  try {
    redevelopCustomerOptions.value = await searchLeadCustomers(q);
  } catch (error) {
    ElMessage.error("搜索客户失败");
    redevelopCustomerOptions.value = [];
  } finally {
    redevelopSearchLoading.value = false;
  }
}

async function createRedevelopLead() {
  if (!redevelopForm.customer_id) {
    ElMessage.warning("请先搜索并选择客户");
    return;
  }
  const selected = redevelopCustomerOptions.value.find((item) => item.id === redevelopForm.customer_id);
  if (!selected) {
    ElMessage.warning("请选择有效客户");
    return;
  }
  creatingRedevelopLead.value = true;
  try {
    await apiClient.post("/leads", {
      template_type: "REDEVELOP",
      related_customer_id: selected.id,
      name: selected.name,
      contact_name: selected.contact_name,
      phone: selected.phone,
      source: redevelopForm.source.trim() || "老客户二次开发",
      intro: selected.source_intro || "",
      notes: redevelopForm.notes.trim(),
      next_reminder_at: redevelopForm.next_reminder_at,
    });
    showRedevelopDialog.value = false;
    ElMessage.success("已创建老客二开线索");
    await fetchLeads();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "创建老客二开线索失败");
  } finally {
    creatingRedevelopLead.value = false;
  }
}

function openFollowupDialog(lead: LeadItem) {
  const grade = lead.grade || "意向中";
  Object.assign(followupForm, createLeadFollowupForm(todayInBrowserTimeZone()), {
    lead_id: lead.id,
    grade,
    reminder_value: lead.reminder_value || getDefaultReminderValueForGrade(grade),
    next_reminder_at: lead.next_reminder_at,
  });
  showFollowupDialog.value = true;
}

function getNextFollowupLeadId(currentLeadId: number) {
  const currentIndex = rows.value.findIndex((item) => item.id === currentLeadId);
  if (currentIndex < 0 || currentIndex >= rows.value.length - 1) return null;
  return rows.value[currentIndex + 1]?.id ?? null;
}

function startLeadFollowupQueue() {
  const firstLead = rows.value[0];
  if (!firstLead) {
    ElMessage.warning("当前没有可连续跟进的线索");
    return;
  }
  openFollowupDialog(firstLead);
}

async function handleLeadRouteQueue() {
  if (leadRouteQueueHandling.value || !isMobileWorkflow.value) return;
  const queue = String(route.query.queue || "").trim();
  if (queue !== "followup") return;

  leadRouteQueueHandling.value = true;
  try {
    Object.assign(filters, createLeadFilters(), {
      status: "FOLLOWING",
      template_type: "",
    });
    await fetchLeads();

    const nextQuery = { ...route.query };
    delete nextQuery.queue;
    await router.replace({ path: route.path, query: nextQuery });

    if (!rows.value.length) {
      ElMessage.warning("当前没有可连续跟进的线索");
      return;
    }
    startLeadFollowupQueue();
  } finally {
    leadRouteQueueHandling.value = false;
  }
}

async function submitFollowup(mode: "close" | "next" = "close") {
  if (!followupForm.lead_id || !followupForm.feedback.trim()) {
    ElMessage.warning("请填写跟进反馈");
    return;
  }

  const nextLeadId = mode === "next" ? getNextFollowupLeadId(followupForm.lead_id) : null;
  try {
    await apiClient.post(`/leads/${followupForm.lead_id}/followups`, followupForm);
    await fetchLeads();
    if (mode === "next" && nextLeadId && isMobileWorkflow.value) {
      const nextLead = rows.value.find((item) => item.id === nextLeadId);
      if (nextLead) {
        ElMessage.success("开发跟进已保存，已切到下一条");
        openFollowupDialog(nextLead);
        return;
      }
    }
    ElMessage.success(mode === "next" ? "开发跟进已保存，已到最后一条" : "开发跟进已保存");
    showFollowupDialog.value = false;
  } catch (error) {
    ElMessage.error("保存跟进失败");
  }
}

async function openConvertDialog(lead: LeadItem) {
  if (!canConvert.value) {
    ElMessage.warning("当前角色没有转化权限");
    return;
  }
  if (lead.status === "CONVERTED") {
    ElMessage.warning("该线索已转化");
    return;
  }
  await ensureAccountantsLoaded();
  convertTargetLeadName.value = lead.name;
  const preferredResponsible = userOptions.value.find((item) => item.id === lead.owner_id);
  const preferredAccountant = accountantOptions.value.find((item) => item.id === lead.owner_id);
  Object.assign(convertForm, createLeadConvertForm(), {
    lead_id: lead.id,
    responsible_user_id: preferredResponsible?.id ?? userOptions.value[0]?.id ?? null,
    assigned_accountant_id: preferredAccountant?.id ?? null,
    customer_name: lead.name,
    customer_contact_name: lead.contact_name,
    customer_phone: lead.phone,
    customer_code_suffix: lead.source === "Sally直播" ? "S" : lead.source === "麦总" || lead.intro === "麦总" ? "M" : "A",
    conversion_mode: "NEW_CUSTOMER_LINKED",
  });
  showConvertDialog.value = true;
}

function resetConvertBillingRows(customerId: number | null = null) {
  convertBillingRows.value = [createEmptyBillingDraft(customerId)];
}

function validateConvertForm(): boolean {
  if (!convertForm.lead_id || !convertForm.responsible_user_id) {
    ElMessage.warning("请先选择负责人员");
    return false;
  }
  if (
    convertForm.conversion_mode === "NEW_CUSTOMER_LINKED" &&
    (!convertForm.customer_name.trim() || !convertForm.customer_contact_name.trim())
  ) {
    ElMessage.warning("请补充转化后的客户名称和联系人");
    return false;
  }
  return true;
}

async function performConvert(): Promise<{ id: number; name: string } | null> {
  if (!validateConvertForm()) return null;
  converting.value = true;
  try {
    const selectedResponsible = userOptions.value.find((item) => item.id === convertForm.responsible_user_id);
    const effectiveAssignedAccountantId =
      convertForm.assigned_accountant_id
      || (selectedResponsible?.role === "ACCOUNTANT" ? selectedResponsible.id : undefined);
    const resp = await apiClient.post<{ customer: { id: number; name: string } }>(
      `/leads/${convertForm.lead_id}/convert`,
      {
        responsible_user_id: convertForm.responsible_user_id,
        assigned_accountant_id: effectiveAssignedAccountantId,
        customer_name: convertForm.customer_name.trim(),
        customer_contact_name: convertForm.customer_contact_name.trim(),
        customer_phone: convertForm.customer_phone.trim(),
        customer_code_seq: convertForm.customer_code_seq || undefined,
        customer_code_suffix: convertForm.customer_code_suffix.trim() || undefined,
        conversion_mode: convertForm.conversion_mode,
      },
    );
    showConvertDialog.value = false;
    await fetchLeads();
    return {
      id: resp.data.customer.id,
      name: resp.data.customer.name,
    };
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "转化失败，可能已转化或无权限");
    return null;
  } finally {
    converting.value = false;
  }
}

async function submitConvert() {
  const customer = await performConvert();
  if (!customer) return;
  ElMessage.success("已转化为客户");
  router.push(`${isMobileWorkflow.value ? "/m/customers" : "/customers"}/${customer.id}?from=leads`);
}

async function submitConvertAndAddBilling() {
  const customer = await performConvert();
  if (!customer) return;
  ElMessage.success("已转化为客户，请继续填写收费信息");
  resetConvertBillingRows(customer.id);
  convertBillingTargetName.value = customer.name;
  showConvertBillingDialog.value = true;
}

async function submitConvertBilling() {
  const validationError = convertBillingRows.value
    .map((item, index) => validateBillingDraft(item, index))
    .find((item) => item);
  if (validationError) {
    ElMessage.warning(validationError);
    return;
  }
  creatingConvertBilling.value = true;
  try {
    const payload = prepareBillingDraftsForSubmit(convertBillingRows.value);
    const resp = await apiClient.post<BillingRecord[]>("/billing-records/batch", { records: payload });
    showConvertBillingDialog.value = false;
    ElMessage.success(`已完成转化并创建 ${resp.data.length} 条收费记录`);
    router.push(isMobileWorkflow.value ? "/m/billing" : "/billing");
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "收费信息保存失败");
  } finally {
    creatingConvertBilling.value = false;
  }
}

async function revokeConvert(lead: LeadItem) {
  if (!canConvert.value) {
    ElMessage.warning("当前角色没有撤销权限");
    return;
  }
  try {
    await ElMessageBox.confirm(
      "撤销后会删除该客户档案（如果已有关联收费记录将不允许撤销）。是否继续？",
      "撤销转化",
      {
        type: "warning",
        confirmButtonText: "确认撤销",
        cancelButtonText: "取消",
      },
    );
    await apiClient.post(`/leads/${lead.id}/unconvert`, {});
    ElMessage.success("已撤销转化");
    await fetchLeads();
  } catch (error: any) {
    if (error === "cancel") {
      return;
    }
    ElMessage.error(error?.response?.data?.detail ?? "撤销失败");
  }
}

async function removeLead(lead: LeadItem) {
  if (!canDeleteLead.value) {
    ElMessage.warning("只有老板和管理员可以删除线索");
    return;
  }
  try {
    await apiClient.delete(`/leads/${lead.id}`);
    ElMessage.success("线索已删除");
    await fetchLeads();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "删除线索失败");
  }
}

async function confirmRemoveLead(lead: LeadItem) {
  try {
    await ElMessageBox.confirm(
      "删除线索后会进入回收站。已转化线索需要先撤销转化，再删除。",
      "删除线索",
      {
        type: "warning",
        confirmButtonText: "确认删除",
        cancelButtonText: "取消",
      },
    );
    await removeLead(lead);
  } catch (error: any) {
    if (error === "cancel" || error?.message === "cancel") return;
    ElMessage.error(error?.response?.data?.detail ?? "删除线索失败");
  }
}

function openLeadDetail(lead: LeadItem) {
  router.push(`${isMobileWorkflow.value ? "/m/leads" : "/leads"}/${lead.id}`);
}

function openCompanyPage(lead: LeadItem) {
  if (lead.status === "CONVERTED" && lead.customer_id) {
    router.push(`${isMobileWorkflow.value ? "/m/customers" : "/customers"}/${lead.customer_id}?from=leads`);
    return;
  }
  router.push(`${isMobileWorkflow.value ? "/m/leads" : "/leads"}/${lead.id}`);
}

function openCustomerArchive(lead: LeadItem) {
  if (!lead.customer_id) {
    ElMessage.warning("该线索尚未转化");
    return;
  }
  router.push(`${isMobileWorkflow.value ? "/m/customers" : "/customers"}/${lead.customer_id}?from=leads`);
}

function openCreateLeadDialog() {
  resetLeadForm();
  showLeadDialog.value = true;
}

function resetLeadForm() {
  Object.assign(leadForm, createLeadForm());
}

function notifyImportTodo() {
  ElMessage.info("已完成字段建模，下一步接 Excel 导入");
}

function resetFiltersAndQuery() {
  Object.assign(filters, createLeadFilters());
  leadMobileFilterMemory.clearState();
  void fetchLeads();
}

function removeLeadFilterChip(key: "keyword" | "status" | "template_type") {
  if (key === "keyword") filters.keyword = "";
  if (key === "status") filters.status = "";
  if (key === "template_type") filters.template_type = "";
  void applyLeadFilters();
}

function toggleLeadExpanded(leadId: number) {
  expandedLeadId.value = expandedLeadId.value === leadId ? null : leadId;
}

function mobileLeadMeta(row: LeadItem): string {
  return [
    getLeadAreaText(row) || "",
    getLeadStartText(row) || "",
    row.next_reminder_at ? `下次 ${row.next_reminder_at}` : "",
  ]
    .filter(Boolean)
    .join(" · ");
}

function mobileLeadSignals(row: LeadItem) {
  return [
    { label: "电话", value: row.phone || "-" },
    { label: "等级", value: row.grade || "-" },
    { label: "最后跟进", value: row.last_followup_date || "未记录" },
    { label: "提醒频率", value: row.reminder_value || "未设置" },
  ];
}

function mobileLeadFacts(row: LeadItem) {
  return [
    row.source ? `来源 ${row.source}` : "",
    getLeadAreaText(row) !== "-" ? `地区 ${getLeadAreaText(row)}` : "",
    getLeadStartText(row) !== "-" ? `起始 ${getLeadStartText(row)}` : "",
  ].filter(Boolean);
}

function mobileLeadBriefs(row: LeadItem) {
  return [
    row.main_business ? { label: "主营/需求", value: row.main_business } : null,
    row.intro ? { label: "介绍人", value: row.intro } : null,
    row.notes ? { label: "备注", value: row.notes } : null,
  ].filter(Boolean) as Array<{ label: string; value: string }>;
}

function restoreSavedLeadFilters() {
  leadMobileFilterMemory.restoreSavedState((snapshot) => {
    Object.assign(filters, createLeadFilters(), snapshot);
  });
}

async function applyLeadFilters() {
  if (isMobileWorkflow.value) {
    leadMobileFilterMemory.saveState(currentLeadFilterSnapshot());
  }
  await fetchLeads();
}

async function applyLeadQuickFilter(mode: "all" | "following" | "new" | "redevelop") {
  if (mode === "all") {
    filters.status = "";
    filters.template_type = "";
  }
  if (mode === "following") {
    filters.status = "FOLLOWING";
    filters.template_type = "";
  }
  if (mode === "new") {
    filters.status = "NEW";
    filters.template_type = "";
  }
  if (mode === "redevelop") {
    filters.status = "";
    filters.template_type = "REDEVELOP";
  }
  await applyLeadFilters();
}

function handlePageCommand(command: string) {
  if (command === "redevelop") openRedevelopDialog();
  if (command === "guide") showGuideDialog.value = true;
  if (command === "import") notifyImportTodo();
}

function handleMobileMenuCommand(command: string, row: LeadItem) {
  if (command === "detail") openLeadDetail(row);
  if (command === "history") void openHistoryDrawer(row);
  if (command === "customer") openCustomerArchive(row);
  if (command === "convert") void openConvertDialog(row);
  if (command === "revoke") void revokeConvert(row);
  if (command === "delete") void removeLead(row);
}

function canQuickConvertLead(row: LeadItem) {
  return canConvert.value && row.status !== "CONVERTED";
}

function leadQuickActionLabel(row: LeadItem) {
  return canQuickConvertLead(row) ? "转化" : "历史";
}

function handleLeadQuickAction(row: LeadItem) {
  if (canQuickConvertLead(row)) {
    void openConvertDialog(row);
    return;
  }
  void openHistoryDrawer(row);
}

function openLeadRowActions(row: LeadItem) {
  selectedLeadActionRow.value = row;
  showLeadRowActionSheet.value = true;
}

function handleLeadRowActionSelect(action: string) {
  if (!selectedLeadActionRow.value) return;
  if (action === "delete") {
    void confirmRemoveLead(selectedLeadActionRow.value);
    return;
  }
  handleMobileMenuCommand(action, selectedLeadActionRow.value);
}

async function openHistoryDrawer(lead: LeadItem) {
  historyLeadName.value = lead.name;
  historyLoading.value = true;
  showHistoryDrawer.value = true;
  try {
    const resp = await apiClient.get<FollowupItem[]>(`/leads/${lead.id}/followups`);
    historyRows.value = resp.data;
  } catch (error) {
    ElMessage.error("加载跟进历史失败");
    historyRows.value = [];
  } finally {
    historyLoading.value = false;
  }
}

onMounted(async () => {
  leadSortBy.value = String(route.query.sort_by || "id");
  leadSortOrder.value = route.query.sort_order === "asc" ? "asc" : "desc";
  if (isMobileWorkflow.value) {
    restoreSavedLeadFilters();
  }
  await fetchLeads();
  await handleLeadRouteQueue();
});

watch(
  () => route.fullPath,
  () => {
    void handleLeadRouteQueue();
  },
);
</script>

<template>
  <template v-if="isMobileWorkflow">
    <section class="mobile-page lead-mobile-page">
      <section class="mobile-shell-panel">
        <div class="mobile-toolbar">
          <div class="mobile-toolbar-main">
            <el-input
              v-model="filters.keyword"
              placeholder="客户 / 联系人 / 电话"
              clearable
              @keyup.enter="applyLeadFilters"
            />
          </div>
          <div class="mobile-toolbar-actions">
            <el-button class="mobile-row-secondary-button" plain :icon="Filter" @click="showMobileFilters = true">
              筛选
            </el-button>
            <el-button class="mobile-row-primary-button" type="primary" @click="openCreateLeadDialog">新增线索</el-button>
            <el-button class="mobile-row-secondary-button" plain @click="showLeadPageActionSheet = true">
              操作
              <el-icon class="el-icon--right"><MoreFilled /></el-icon>
            </el-button>
          </div>
        </div>
        <div class="mobile-filter-presets">
          <button
            v-for="item in leadQuickFilters"
            :key="item.key"
            type="button"
            class="mobile-filter-preset"
            :class="{ active: item.active }"
            @click="applyLeadQuickFilter(item.key)"
          >
            {{ item.label }}
          </button>
        </div>
        <div v-if="activeFilterChips.length" class="mobile-chip-row lead-mobile-chip-row">
          <button
            v-for="chip in leadFilterChips"
            :key="chip.key"
            type="button"
            class="mobile-chip-button"
            @click="removeLeadFilterChip(chip.key)"
          >
            <span>{{ chip.label }}</span>
            <span class="mobile-chip-close">移除</span>
          </button>
          <button type="button" class="lead-clear-chip" @click="resetFiltersAndQuery">清空</button>
        </div>
      </section>

      <section class="mobile-shell-panel lead-mobile-list-panel">
        <div v-if="rows.length" class="mobile-queue-strip">
          <div class="mobile-queue-main">
            <div class="mobile-queue-kicker">连续跟进</div>
            <div class="mobile-queue-copy">按当前筛选顺序处理 {{ rows.length }} 条线索。</div>
          </div>
          <el-button class="mobile-row-secondary-button" size="small" plain @click="startLeadFollowupQueue">
            从首条开始
          </el-button>
        </div>
        <div class="lead-mobile-head">
          <div>
            <div class="lead-mobile-title">客户开发</div>
            <div class="lead-mobile-copy">先看状态和提醒，再直接跟进或转化。</div>
          </div>
          <div v-if="showLeadInitialSkeleton" class="mobile-skeleton-chip lead-mobile-count-skeleton"></div>
          <el-tag v-else class="mobile-count-tag" effect="plain">{{ rows.length }} 条</el-tag>
        </div>

        <div v-loading="loading && leadsHydrated" class="lead-mobile-list">
          <template v-if="showLeadInitialSkeleton">
            <article v-for="index in 4" :key="`lead-skeleton-${index}`" class="lead-mobile-row lead-mobile-skeleton-row">
              <div class="lead-mobile-row-top">
                <div class="mobile-skeleton-line is-lg"></div>
                <div class="lead-mobile-skeleton-tags">
                  <div class="mobile-skeleton-chip"></div>
                  <div class="mobile-skeleton-chip"></div>
                </div>
              </div>
              <div class="mobile-skeleton-stack">
                <div class="mobile-skeleton-line is-md"></div>
                <div class="mobile-skeleton-line is-xl"></div>
              </div>
              <div class="lead-mobile-skeleton-actions">
                <div class="mobile-skeleton-button"></div>
                <div class="mobile-skeleton-button"></div>
              </div>
            </article>
          </template>
          <div v-else-if="!rows.length" class="mobile-empty-block">
            <div class="mobile-empty-kicker">客户开发</div>
            <div class="mobile-empty-title">当前没有匹配的线索</div>
            <div class="mobile-empty-copy">换个状态、关键词或快速筛选，继续收口当前线索池。</div>
          </div>
          <article v-for="row in rows" :key="row.id" class="lead-mobile-row">
            <div class="lead-mobile-row-top">
              <button type="button" class="lead-mobile-name" @click="openCompanyPage(row)">{{ row.name }}</button>
              <div class="lead-mobile-tags">
                <el-tag class="mobile-status-tag" size="small" effect="plain">{{ getTemplateLabel(row.template_type) }}</el-tag>
                <el-tag class="mobile-status-tag" size="small" :type="statusTagType(row.status)">
                  {{ getStatusLabel(row.status) }}
                </el-tag>
              </div>
            </div>
            <div class="lead-mobile-summary">{{ getLeadContactText(row) || "未填写联系人" }}</div>
            <div class="lead-mobile-meta">{{ mobileLeadMeta(row) || "暂无提醒信息" }}</div>

            <transition name="lead-expand">
              <div v-if="expandedLeadId === row.id" class="lead-mobile-expanded">
                <div class="lead-mobile-signal-grid">
                  <div v-for="item in mobileLeadSignals(row)" :key="`${row.id}-${item.label}`" class="lead-mobile-signal">
                    <span>{{ item.label }}</span>
                    <strong>{{ item.value }}</strong>
                  </div>
                </div>
                <div v-if="mobileLeadFacts(row).length" class="lead-mobile-fact-row">
                  <span v-for="fact in mobileLeadFacts(row)" :key="`${row.id}-${fact}`" class="lead-mobile-fact-chip">
                    {{ fact }}
                  </span>
                </div>
                <div v-if="mobileLeadBriefs(row).length" class="lead-mobile-brief-list">
                  <div
                    v-for="item in mobileLeadBriefs(row)"
                    :key="`${row.id}-${item.label}`"
                    class="lead-mobile-brief"
                  >
                    <span>{{ item.label }}</span>
                    <strong>{{ item.value }}</strong>
                  </div>
                </div>
              </div>
            </transition>

            <div class="mobile-action-stack lead-mobile-actions">
              <div class="mobile-action-main">
                <el-button class="mobile-row-primary-button" size="small" type="primary" @click="openFollowupDialog(row)">
                  跟进
                </el-button>
                <el-button class="mobile-row-secondary-button" size="small" plain @click="handleLeadQuickAction(row)">
                  {{ leadQuickActionLabel(row) }}
                </el-button>
              </div>
              <div class="mobile-action-sub">
                <button type="button" class="mobile-action-link is-muted" @click="toggleLeadExpanded(row.id)">
                  {{ expandedLeadId === row.id ? "收起补充信息" : "展开补充信息" }}
                </button>
                <button type="button" class="mobile-action-link" @click="openLeadDetail(row)">查看详情</button>
                <button type="button" class="mobile-action-link" @click="openLeadRowActions(row)">更多操作</button>
              </div>
            </div>
          </article>
        </div>
      </section>
    </section>

    <MobileFilterSheet
      v-model="showMobileFilters"
      title="筛选线索"
      subtitle="先缩小范围，再回列表连续处理。"
      :summary-items="activeFilterChips"
      empty-summary="当前未设置筛选条件"
    >
      <el-form label-position="top" class="lead-mobile-filter-form">
        <div v-if="leadMobileFilterMemory.hasSavedState.value" class="mobile-filter-restore">
          <el-button text type="primary" @click="restoreSavedLeadFilters">恢复上次已应用条件</el-button>
        </div>
        <el-form-item label="关键词">
          <el-input
            v-model="filters.keyword"
            placeholder="客户 / 联系人 / 电话"
            clearable
            @keyup.enter="applyLeadFilters"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable>
            <el-option label="新线索" value="NEW" />
            <el-option label="跟进中" value="FOLLOWING" />
            <el-option label="已转化" value="CONVERTED" />
            <el-option label="已丢失" value="LOST" />
          </el-select>
        </el-form-item>
        <el-form-item label="模板">
          <el-select v-model="filters.template_type" placeholder="全部" clearable>
            <el-option label="客户跟进模板" value="FOLLOWUP" />
            <el-option label="客户转化模板" value="CONVERSION" />
            <el-option label="老客二开模板" value="REDEVELOP" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetFiltersAndQuery">重置</el-button>
        <el-button type="primary" @click="showMobileFilters = false; applyLeadFilters()">应用筛选</el-button>
      </template>
    </MobileFilterSheet>

    <MobileActionSheet
      v-model="showLeadPageActionSheet"
      title="页面操作"
      subtitle="这些都是低频入口，统一收在这里。"
      :items="leadPageActionItems"
      @select="handlePageCommand"
    />

    <MobileActionSheet
      v-model="showLeadRowActionSheet"
      title="线索操作"
      :subtitle="selectedLeadActionRow?.name || ''"
      :items="leadRowActionItems"
      @select="handleLeadRowActionSelect"
    />
  </template>

  <el-space v-else direction="vertical" fill :size="12">
    <LeadFilterCard
      :filters="filters"
      @query="fetchLeads"
      @create="openCreateLeadDialog"
      @redevelop="openRedevelopDialog"
      @guide="showGuideDialog = true"
      @import-excel="notifyImportTodo"
    />
    <LeadOverviewCard
      :loading="loading"
      :rows="rows"
      :can-convert="canConvert"
      :can-delete="canDeleteLead"
      :sort-prop="leadSortBy"
      :sort-order="leadSortOrderForTable()"
      @company="openCompanyPage"
      @detail="openLeadDetail"
      @customer="openCustomerArchive"
      @followup="openFollowupDialog"
      @history="openHistoryDrawer"
      @convert="openConvertDialog"
      @revoke="revokeConvert"
      @delete="removeLead"
      @sort-change="handleLeadSortChange"
    />
  </el-space>

  <LeadCreateDialog v-model:visible="showLeadDialog" :form="leadForm" @submit="createLead" />

  <LeadRedevelopDialog
    v-model:visible="showRedevelopDialog"
    :form="redevelopForm"
    :options="redevelopCustomerOptions"
    :search-loading="redevelopSearchLoading"
    :submitting="creatingRedevelopLead"
    @search="searchRedevelopCustomers"
    @submit="createRedevelopLead"
  />

  <LeadFollowupDialog
    v-model:visible="showFollowupDialog"
    :form="followupForm"
    :queue-label="isMobileWorkflow ? mobileFollowupQueueLabel : ''"
    :show-next-action="isMobileWorkflow && hasNextFollowupLead"
    @submit="submitFollowup()"
    @submit-next="submitFollowup('next')"
  />

  <LeadConvertDialog
    v-model:visible="showConvertDialog"
    :target-lead-name="convertTargetLeadName"
    :form="convertForm"
    :user-options="userOptions"
    :accountant-options="accountantOptions"
    :loading="converting"
    @submit="submitConvert"
    @submit-and-add-billing="submitConvertAndAddBilling"
  />

  <LeadConvertBillingDialog
    v-model:visible="showConvertBillingDialog"
    v-model:rows="convertBillingRows"
    :customer-name="convertBillingTargetName"
    :loading="creatingConvertBilling"
    @submit="submitConvertBilling"
  />

  <LeadGuideDialog v-model:visible="showGuideDialog" />

  <LeadHistoryDrawer
    v-model:visible="showHistoryDrawer"
    :lead-name="historyLeadName"
    :loading="historyLoading"
    :rows="historyRows"
  />
</template>

<style scoped>
.lead-mobile-page {
  gap: 12px;
}

.lead-mobile-chip-row {
  margin-top: 12px;
}

.lead-clear-chip {
  border: none;
  background: transparent;
  padding: 0;
  color: var(--app-accent-strong);
  font-size: 12px;
}

.lead-mobile-list-panel {
  padding-top: 12px;
}

.lead-mobile-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.lead-mobile-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.lead-mobile-copy {
  margin-top: 3px;
  font-size: 12px;
  color: var(--app-text-muted);
}

.lead-mobile-count-skeleton {
  flex-shrink: 0;
}

.lead-mobile-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 14px;
}

.lead-mobile-skeleton-row {
  gap: 10px;
}

.lead-mobile-skeleton-tags,
.lead-mobile-skeleton-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.lead-mobile-skeleton-actions {
  justify-content: flex-start;
}

.lead-mobile-row {
  border-top: 1px solid var(--app-border-soft);
  padding-top: 12px;
}

.lead-mobile-row:first-child {
  border-top: none;
  padding-top: 0;
}

.lead-mobile-row-top {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.lead-mobile-name {
  border: none;
  padding: 0;
  background: transparent;
  text-align: left;
  font-size: 15px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.lead-mobile-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.lead-mobile-summary {
  margin-top: 6px;
  font-size: 13px;
  color: var(--app-text-secondary);
}

.lead-mobile-meta {
  margin-top: 4px;
  font-size: 12px;
  color: var(--app-text-muted);
}

.lead-mobile-expanded {
  margin-top: 10px;
  padding: 10px 0 0;
  border-top: 1px dashed var(--app-border-soft);
}

.lead-mobile-signal-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.lead-mobile-signal {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  background: color-mix(in srgb, var(--app-bg-soft) 70%, white 30%);
  border: 1px solid var(--app-border-soft);
  border-radius: 14px;
}

.lead-mobile-signal span {
  font-size: 11px;
  color: var(--app-text-muted);
}

.lead-mobile-signal strong {
  font-size: 13px;
  line-height: 1.4;
  color: var(--app-text-primary);
}

.lead-mobile-fact-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.lead-mobile-fact-chip {
  padding: 5px 10px;
  border-radius: 999px;
  background: var(--app-bg-soft);
  font-size: 11px;
  color: var(--app-text-muted);
}

.lead-mobile-brief-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
}

.lead-mobile-brief {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 8px;
  font-size: 12px;
  line-height: 1.55;
}

.lead-mobile-brief span {
  color: var(--app-text-muted);
}

.lead-mobile-brief strong {
  font-size: 12px;
  font-weight: 500;
  color: var(--app-text-secondary);
  word-break: break-word;
}

.lead-mobile-actions {
  margin-top: 12px;
}

.lead-mobile-filter-form :deep(.el-form-item) {
  margin-bottom: 14px;
}

.mobile-filter-restore {
  display: flex;
  justify-content: flex-start;
  margin-bottom: 6px;
}

.lead-expand-enter-active,
.lead-expand-leave-active {
  transition: opacity 180ms ease, transform 180ms ease;
}

.lead-expand-enter-from,
.lead-expand-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
