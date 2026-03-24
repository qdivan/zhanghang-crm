<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";

import { apiClient } from "../api/client";
import LeadConvertBillingDialog from "../components/leads/LeadConvertBillingDialog.vue";
import LeadConvertDialog from "../components/leads/LeadConvertDialog.vue";
import LeadCreateDialog from "../components/leads/LeadCreateDialog.vue";
import LeadFilterCard from "../components/leads/LeadFilterCard.vue";
import LeadFollowupDialog from "../components/leads/LeadFollowupDialog.vue";
import LeadGuideDialog from "../components/leads/LeadGuideDialog.vue";
import LeadHistoryDrawer from "../components/leads/LeadHistoryDrawer.vue";
import LeadOverviewCard from "../components/leads/LeadOverviewCard.vue";
import LeadRedevelopDialog from "../components/leads/LeadRedevelopDialog.vue";
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
import { getDefaultReminderValueForGrade, sortLeadRows } from "./lead/viewMeta";

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
const router = useRouter();
const loading = ref(false);
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
const accountantOptions = ref<UserLite[]>([]);
const converting = ref(false);
const creatingConvertBilling = ref(false);
const creatingRedevelopLead = ref(false);
const redevelopSearchLoading = ref(false);
const redevelopCustomerOptions = ref<LeadCustomerSearchItem[]>([]);
const redevelopForm = reactive<LeadRedevelopForm>(createLeadRedevelopForm());
const convertForm = reactive<LeadConvertForm>(createLeadConvertForm());
const convertBillingRows = ref<BillingCreatePayload[]>([createEmptyBillingDraft(null)]);

const filters = reactive(createLeadFilters());
const leadForm = reactive<LeadCreateForm>(createLeadForm());
const followupForm = reactive<LeadFollowupForm>(createLeadFollowupForm(todayInBrowserTimeZone()));

const canConvert = computed(
  () => auth.user?.role === "OWNER" || auth.user?.role === "ADMIN" || auth.user?.role === "MANAGER",
);

async function fetchLeads() {
  loading.value = true;
  try {
    const resp = await apiClient.get<LeadItem[]>("/leads", {
      params: {
        keyword: filters.keyword || undefined,
        status: filters.status || undefined,
      },
    });
    const activeLeadRows = resp.data.filter((item) => item.status !== "CONVERTED");
    const filtered = filters.template_type
      ? activeLeadRows.filter((item) => item.template_type === filters.template_type)
      : activeLeadRows;
    rows.value = sortLeadRows(filtered);
  } catch (error) {
    ElMessage.error("获取线索失败");
  } finally {
    loading.value = false;
  }
}

async function createLead() {
  if (!leadForm.name || !leadForm.contact_name || !leadForm.phone) {
    ElMessage.warning("请填写完整客户名称、联系人和电话");
    return;
  }

  try {
    let autoLinkedCustomerName = "";
    if (!leadForm.related_customer_id) {
      const exactCustomer = await findExactLeadCustomer(leadForm.name);
      if (exactCustomer) {
        leadForm.related_customer_id = exactCustomer.id;
        autoLinkedCustomerName = exactCustomer.name;
      }
    }

    await apiClient.post("/leads", leadForm);
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

async function fetchAccountants() {
  if (!canConvert.value) {
    accountantOptions.value = [];
    return;
  }
  try {
    const resp = await apiClient.get<UserLite[]>("/users", {
      params: { role: "ACCOUNTANT" },
    });
    accountantOptions.value = resp.data;
  } catch (error) {
    ElMessage.error("获取会计列表失败");
  }
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

async function submitFollowup() {
  if (!followupForm.lead_id || !followupForm.feedback.trim()) {
    ElMessage.warning("请填写跟进反馈");
    return;
  }

  try {
    await apiClient.post(`/leads/${followupForm.lead_id}/followups`, followupForm);
    ElMessage.success("开发跟进已保存");
    showFollowupDialog.value = false;
    await fetchLeads();
  } catch (error) {
    ElMessage.error("保存跟进失败");
  }
}

function openConvertDialog(lead: LeadItem) {
  if (!canConvert.value) {
    ElMessage.warning("当前角色没有转化权限");
    return;
  }
  if (lead.status === "CONVERTED") {
    ElMessage.warning("该线索已转化");
    return;
  }
  convertTargetLeadName.value = lead.name;
  const preferred = accountantOptions.value.find((item) => item.id === lead.owner_id);
  Object.assign(convertForm, createLeadConvertForm(), {
    lead_id: lead.id,
    accountant_id: preferred?.id ?? accountantOptions.value[0]?.id ?? null,
    customer_name: lead.name,
    customer_contact_name: lead.contact_name,
    customer_phone: lead.phone,
  });
  showConvertDialog.value = true;
}

function resetConvertBillingRows(customerId: number | null = null) {
  convertBillingRows.value = [createEmptyBillingDraft(customerId)];
}

function validateConvertForm(): boolean {
  if (!convertForm.lead_id || !convertForm.accountant_id) {
    ElMessage.warning("请先选择分配会计");
    return false;
  }
  if (
    !convertForm.customer_name.trim() ||
    !convertForm.customer_contact_name.trim() ||
    !convertForm.customer_phone.trim()
  ) {
    ElMessage.warning("请补充转化后的客户名称、联系人和电话");
    return false;
  }
  return true;
}

async function performConvert(): Promise<{ id: number; name: string } | null> {
  if (!validateConvertForm()) return null;
  converting.value = true;
  try {
    const resp = await apiClient.post<{ customer: { id: number } }>(
      `/leads/${convertForm.lead_id}/convert`,
      {
        accountant_id: convertForm.accountant_id,
        customer_name: convertForm.customer_name.trim(),
        customer_contact_name: convertForm.customer_contact_name.trim(),
        customer_phone: convertForm.customer_phone.trim(),
      },
    );
    showConvertDialog.value = false;
    await fetchLeads();
    return {
      id: resp.data.customer.id,
      name: convertForm.customer_name.trim(),
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
  router.push(`/customers/${customer.id}?from=leads`);
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
    router.push("/billing");
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

function openLeadDetail(lead: LeadItem) {
  router.push(`/leads/${lead.id}`);
}

function openCompanyPage(lead: LeadItem) {
  if (lead.status === "CONVERTED" && lead.customer_id) {
    router.push(`/customers/${lead.customer_id}?from=leads`);
    return;
  }
  router.push(`/leads/${lead.id}`);
}

function openCustomerArchive(lead: LeadItem) {
  if (!lead.customer_id) {
    ElMessage.warning("该线索尚未转化");
    return;
  }
  router.push(`/customers/${lead.customer_id}?from=leads`);
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
  await fetchLeads();
  await fetchAccountants();
});
</script>

<template>
  <el-space direction="vertical" fill :size="12">
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
      @company="openCompanyPage"
      @detail="openLeadDetail"
      @customer="openCustomerArchive"
      @followup="openFollowupDialog"
      @history="openHistoryDrawer"
      @convert="openConvertDialog"
      @revoke="revokeConvert"
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
    @submit="submitFollowup"
  />

  <LeadConvertDialog
    v-model:visible="showConvertDialog"
    :target-lead-name="convertTargetLeadName"
    :form="convertForm"
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
