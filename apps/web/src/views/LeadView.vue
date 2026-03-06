<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";

import { apiClient } from "../api/client";
import { useAuthStore } from "../stores/auth";
import type { LeadItem, LeadStatus, LeadTemplateType } from "../types";
import { commitDateInput } from "../utils/dateInput";
import { toEpochMillis, todayInBrowserTimeZone } from "../utils/time";

type LeadCreateForm = {
  template_type: LeadTemplateType;
  name: string;
  grade: string;
  contact_name: string;
  phone: string;
  region: string;
  country: string;
  source: string;
  contact_wechat: string;
  fax: string;
  other_contact: string;
  contact_start_date: string | null;
  service_start_text: string;
  company_nature: string;
  service_mode: string;
  main_business: string;
  intro: string;
  fee_standard: string;
  first_billing_period: string;
  reserve_2: string;
  reserve_3: string;
  reserve_4: string;
  reminder_value: string;
  next_reminder_at: string | null;
  notes: string;
};

type FollowupForm = {
  lead_id: number | null;
  followup_at: string;
  feedback: string;
  notes: string;
  next_reminder_at: string | null;
};

type FollowupItem = {
  id: number;
  lead_id: number;
  followup_at: string;
  feedback: string;
  next_reminder_at: string | null;
  notes: string;
  created_by: number;
  created_at: string;
};

type UserLite = {
  id: number;
  username: string;
  role: string;
};

type CustomerSearchItem = {
  id: number;
  name: string;
  contact_name: string;
  phone: string;
  assigned_accountant_id: number;
  accountant_username: string;
};

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
const redevelopCustomerOptions = ref<CustomerSearchItem[]>([]);
const redevelopForm = reactive({
  customer_id: null as number | null,
  source: "老客户二次开发",
  notes: "",
  next_reminder_at: null as string | null,
});
const convertForm = reactive({
  lead_id: null as number | null,
  accountant_id: null as number | null,
  customer_name: "",
  customer_contact_name: "",
  customer_phone: "",
});
const convertBillingForm = reactive<BillingCreateForm>({
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

const filters = reactive({
  keyword: "",
  status: "",
  template_type: "",
});

const leadForm = reactive<LeadCreateForm>({
  template_type: "FOLLOWUP",
  name: "",
  grade: "",
  contact_name: "",
  phone: "",
  region: "",
  country: "",
  source: "",
  contact_wechat: "",
  fax: "",
  other_contact: "",
  contact_start_date: null,
  service_start_text: "",
  company_nature: "",
  service_mode: "",
  main_business: "",
  intro: "",
  fee_standard: "",
  first_billing_period: "",
  reserve_2: "",
  reserve_3: "",
  reserve_4: "",
  reminder_value: "",
  next_reminder_at: null,
  notes: "",
});

const followupForm = reactive<FollowupForm>({
  lead_id: null,
  followup_at: todayInBrowserTimeZone(),
  feedback: "",
  notes: "",
  next_reminder_at: null,
});

const statusOptions = [
  { label: "新线索", value: "NEW" },
  { label: "跟进中", value: "FOLLOWING" },
  { label: "已转化", value: "CONVERTED" },
  { label: "已丢失", value: "LOST" },
];

const templateOptions = [
  { label: "客户跟进模板", value: "FOLLOWUP" },
  { label: "转化模板", value: "CONVERSION" },
  { label: "老客二开模板", value: "REDEVELOP" },
];

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

const canConvert = computed(() => auth.user?.role === "OWNER" || auth.user?.role === "ADMIN");

const statusLabelMap: Record<LeadStatus, string> = {
  NEW: "新线索",
  FOLLOWING: "跟进中",
  CONVERTED: "已转化",
  LOST: "已丢失",
};

function statusTagType(status: LeadStatus) {
  if (status === "CONVERTED") return "success";
  if (status === "FOLLOWING") return "warning";
  if (status === "LOST") return "info";
  return "primary";
}

function getStatusLabel(status: LeadStatus) {
  return statusLabelMap[status] ?? status;
}

function getTemplateLabel(templateType: LeadTemplateType) {
  if (templateType === "FOLLOWUP") return "客户跟进";
  if (templateType === "REDEVELOP") return "老客二开";
  return "转化";
}

const leadStatusOrder: Record<LeadStatus, number> = {
  FOLLOWING: 0,
  NEW: 1,
  LOST: 2,
  CONVERTED: 3,
};

function sortLeadRows(items: LeadItem[]): LeadItem[] {
  return [...items].sort((a, b) => {
    const statusDiff = (leadStatusOrder[a.status] ?? 9) - (leadStatusOrder[b.status] ?? 9);
    if (statusDiff !== 0) return statusDiff;

    // 对待跟进线索按提醒日期升序，提醒更近的靠前
    if (a.status === "FOLLOWING" || a.status === "NEW") {
      const aReminder = toEpochMillis(a.next_reminder_at);
      const bReminder = toEpochMillis(b.next_reminder_at);
      if (!Number.isNaN(aReminder) || !Number.isNaN(bReminder)) {
        if (Number.isNaN(aReminder)) return 1;
        if (Number.isNaN(bReminder)) return -1;
        if (aReminder !== bReminder) return aReminder - bReminder;
      }
    }

    const aUpdated = toEpochMillis(a.updated_at);
    const bUpdated = toEpochMillis(b.updated_at);
    if (!Number.isNaN(aUpdated) && !Number.isNaN(bUpdated) && aUpdated !== bUpdated) {
      return bUpdated - aUpdated;
    }
    return b.id - a.id;
  });
}

async function fetchLeads() {
  loading.value = true;
  try {
    const resp = await apiClient.get<LeadItem[]>("/leads", {
      params: {
        keyword: filters.keyword || undefined,
        status: filters.status || undefined,
      },
    });
    const filtered = filters.template_type
      ? resp.data.filter((item) => item.template_type === filters.template_type)
      : resp.data;
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
    await apiClient.post("/leads", leadForm);
    ElMessage.success("线索已创建");
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
  redevelopForm.customer_id = null;
  redevelopForm.source = "老客户二次开发";
  redevelopForm.notes = "";
  redevelopForm.next_reminder_at = null;
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
    const resp = await apiClient.get<CustomerSearchItem[]>("/customers", {
      params: { keyword: q },
    });
    redevelopCustomerOptions.value = resp.data.slice(0, 20);
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
  followupForm.lead_id = lead.id;
  followupForm.followup_at = todayInBrowserTimeZone();
  followupForm.feedback = "";
  followupForm.notes = "";
  followupForm.next_reminder_at = lead.next_reminder_at;
  showFollowupDialog.value = true;
}

async function submitFollowup() {
  if (!followupForm.lead_id || !followupForm.feedback.trim()) {
    ElMessage.warning("请填写跟进反馈");
    return;
  }

  try {
    await apiClient.post(`/leads/${followupForm.lead_id}/followups`, followupForm);
    ElMessage.success("跟进记录已保存");
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
  convertForm.lead_id = lead.id;
  convertTargetLeadName.value = lead.name;
  const preferred = accountantOptions.value.find((item) => item.id === lead.owner_id);
  convertForm.accountant_id = preferred?.id ?? accountantOptions.value[0]?.id ?? null;
  convertForm.customer_name = lead.name;
  convertForm.customer_contact_name = lead.contact_name;
  convertForm.customer_phone = lead.phone;
  showConvertDialog.value = true;
}

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

function applyConvertBillingDefaults() {
  if (convertBillingForm.charge_mode === "ONE_TIME") {
    convertBillingForm.amount_basis = "ONE_TIME";
    convertBillingForm.period_start_month = "";
    convertBillingForm.period_end_month = "";
    if (!convertBillingForm.due_month) {
      convertBillingForm.due_month = todayInBrowserTimeZone();
    }
  } else {
    if (convertBillingForm.amount_basis === "ONE_TIME") {
      convertBillingForm.amount_basis = "MONTHLY";
    }
    if (convertBillingForm.period_start_month && !convertBillingForm.period_end_month) {
      convertBillingForm.period_end_month = shiftMonth(convertBillingForm.period_start_month, 11);
    }
  }
}

function onConvertBillingModeChange() {
  applyConvertBillingDefaults();
}

function onConvertBillingStartMonthChange() {
  if (convertBillingForm.charge_mode === "PERIODIC" && convertBillingForm.period_start_month) {
    convertBillingForm.period_end_month = shiftMonth(convertBillingForm.period_start_month, 11);
    convertBillingForm.collection_start_date = `${convertBillingForm.period_start_month}-01`;
  }
}

function resetConvertBillingForm() {
  convertBillingForm.serial_no = null;
  convertBillingForm.customer_id = null;
  convertBillingForm.charge_category = "代账";
  convertBillingForm.charge_mode = "PERIODIC";
  convertBillingForm.amount_basis = "MONTHLY";
  convertBillingForm.summary = "";
  convertBillingForm.total_fee = 0;
  convertBillingForm.monthly_fee = 0;
  convertBillingForm.billing_cycle_text = "按月（每月收）";
  convertBillingForm.period_start_month = "";
  convertBillingForm.period_end_month = "";
  convertBillingForm.collection_start_date = "";
  convertBillingForm.due_month = "";
  convertBillingForm.payment_method = "预收";
  convertBillingForm.status = "PARTIAL";
  convertBillingForm.received_amount = 0;
  convertBillingForm.note = "";
  convertBillingForm.extra_note = "";
  convertBillingForm.color_tag = "";
  applyConvertBillingDefaults();
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
  resetConvertBillingForm();
  convertBillingForm.customer_id = customer.id;
  convertBillingTargetName.value = customer.name;
  showConvertBillingDialog.value = true;
}

async function submitConvertBilling() {
  if (!convertBillingForm.customer_id) {
    ElMessage.warning("客户信息缺失，无法保存收费记录");
    return;
  }
  applyConvertBillingDefaults();
  if (convertBillingForm.charge_mode === "PERIODIC") {
    if (convertBillingForm.period_start_month && !convertBillingForm.collection_start_date) {
      convertBillingForm.collection_start_date = `${convertBillingForm.period_start_month}-01`;
    }
    if (convertBillingForm.period_end_month && !convertBillingForm.due_month) {
      convertBillingForm.due_month = `${convertBillingForm.period_end_month}-28`;
    }
  }
  creatingConvertBilling.value = true;
  try {
    await apiClient.post("/billing-records", convertBillingForm);
    showConvertBillingDialog.value = false;
    ElMessage.success("已完成转化并创建收费记录");
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
  leadForm.template_type = "FOLLOWUP";
  leadForm.name = "";
  leadForm.grade = "";
  leadForm.contact_name = "";
  leadForm.phone = "";
  leadForm.region = "";
  leadForm.country = "";
  leadForm.source = "";
  leadForm.contact_wechat = "";
  leadForm.fax = "";
  leadForm.other_contact = "";
  leadForm.contact_start_date = null;
  leadForm.service_start_text = "";
  leadForm.company_nature = "";
  leadForm.service_mode = "";
  leadForm.main_business = "";
  leadForm.intro = "";
  leadForm.fee_standard = "";
  leadForm.first_billing_period = "";
  leadForm.reserve_2 = "";
  leadForm.reserve_3 = "";
  leadForm.reserve_4 = "";
  leadForm.reminder_value = "";
  leadForm.next_reminder_at = null;
  leadForm.notes = "";
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
    <el-card shadow="never">
      <el-form inline @submit.prevent="fetchLeads" class="lead-filter-form">
        <el-form-item label="关键词">
          <el-input
            v-model="filters.keyword"
            placeholder="客户/联系人/电话"
            clearable
            @keyup.enter="fetchLeads"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable>
            <el-option
              v-for="item in statusOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="模板筛选">
          <el-select v-model="filters.template_type" placeholder="全部" clearable>
            <el-option
              v-for="item in templateOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button @click="fetchLeads">查询</el-button>
          <el-button type="primary" @click="openCreateLeadDialog">新增线索</el-button>
          <el-button type="primary" plain @click="openRedevelopDialog">老客二次开发</el-button>
          <el-button @click="showGuideDialog = true">流程说明</el-button>
          <el-button @click="notifyImportTodo">导入 Excel</el-button>
        </el-form-item>
      </el-form>
      <el-text type="info">
        当前排序：跟进中（按下次提醒） -> 新线索 -> 已丢失 -> 已转化（置底）
      </el-text>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="table-head">
          <span>客户开发总览（首页只保留核心字段）</span>
          <el-tag type="success" effect="plain">{{ rows.length }} 条</el-tag>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe border>
        <el-table-column prop="id" label="序号" width="70" />
        <el-table-column label="模板" width="90">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ getTemplateLabel(row.template_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="公司名" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <el-button link type="primary" @click="openCompanyPage(row)">
              {{ row.name }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column
          prop="contact_name"
          label="联系人"
          width="110"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="phone"
          label="电话"
          width="130"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="source"
          label="来源"
          width="95"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="grade"
          label="等级"
          width="70"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          label="状态"
          width="100"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        >
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="next_reminder_at"
          label="下次提醒"
          width="110"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="last_feedback"
          label="最后跟进反馈"
          min-width="180"
          show-overflow-tooltip
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          label="操作"
          width="250"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        >
          <template #default="{ row }">
            <el-space class="table-action-wrap">
              <el-button link @click="openLeadDetail(row)">详情</el-button>
              <el-button v-if="row.customer_id" link type="primary" @click="openCustomerArchive(row)">
                客户档案
              </el-button>
              <el-button link type="primary" @click="openFollowupDialog(row)">跟进</el-button>
              <el-button link @click="openHistoryDrawer(row)">历史</el-button>
              <el-button
                link
                type="success"
                :disabled="!canConvert || row.status === 'CONVERTED'"
                @click="openConvertDialog(row)"
              >
                转化
              </el-button>
              <el-button
                v-if="row.status === 'CONVERTED'"
                link
                type="danger"
                :disabled="!canConvert"
                @click="revokeConvert(row)"
              >
                撤销转化
              </el-button>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </el-space>

  <el-dialog v-model="showLeadDialog" title="新增线索（Excel 字段版）" width="860px">
    <el-form label-position="top">
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="来源模板">
            <el-select v-model="leadForm.template_type">
              <el-option label="客户跟进模板" value="FOLLOWUP" />
              <el-option label="转化模板" value="CONVERSION" />
              <el-option label="老客二开模板" value="REDEVELOP" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="公司名">
            <el-input v-model="leadForm.name" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="等级">
            <el-input v-model="leadForm.grade" placeholder="A/B/C..." />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="联系人">
            <el-input v-model="leadForm.contact_name" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="电话">
            <el-input v-model="leadForm.phone" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="微信/联系人（微信号）">
            <el-input v-model="leadForm.contact_wechat" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="地区">
            <el-input v-model="leadForm.region" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="国家/业务类型">
            <el-input v-model="leadForm.country" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="来源">
            <el-input v-model="leadForm.source" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="传真">
            <el-input v-model="leadForm.fax" />
          </el-form-item>
        </el-col>
        <el-col :span="16">
          <el-form-item label="其他联系方式">
            <el-input v-model="leadForm.other_contact" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="联络开始时间">
            <el-date-picker
              v-model="leadForm.contact_start_date"
              type="date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              :editable="true"
              placeholder="YYYYMMDD 或 YYMMDD"
              @keydown.enter.capture="commitDateInput((v) => (leadForm.contact_start_date = v), $event)"
              @blur.capture="commitDateInput((v) => (leadForm.contact_start_date = v), $event)"
            />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="服务开始时间（文本）">
            <el-input v-model="leadForm.service_start_text" placeholder="如 2025.07.02" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="下次提醒">
            <el-date-picker
              v-model="leadForm.next_reminder_at"
              type="date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              :editable="true"
              placeholder="YYYYMMDD 或 YYMMDD"
              @keydown.enter.capture="commitDateInput((v) => (leadForm.next_reminder_at = v), $event)"
              @blur.capture="commitDateInput((v) => (leadForm.next_reminder_at = v), $event)"
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="企业性质">
            <el-input v-model="leadForm.company_nature" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="服务方式">
            <el-input v-model="leadForm.service_mode" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="提醒值">
            <el-input v-model="leadForm.reminder_value" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="主营/需求">
        <el-input v-model="leadForm.main_business" type="textarea" :rows="2" />
      </el-form-item>
      <el-form-item label="介绍">
        <el-input v-model="leadForm.intro" />
      </el-form-item>

      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="收费标准">
            <el-input v-model="leadForm.fee_standard" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="首期账单期间">
            <el-input v-model="leadForm.first_billing_period" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="备用2">
            <el-input v-model="leadForm.reserve_2" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="备用3">
            <el-input v-model="leadForm.reserve_3" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="备用4">
            <el-input v-model="leadForm.reserve_4" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="备注">
        <el-input v-model="leadForm.notes" type="textarea" :rows="2" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showLeadDialog = false">取消</el-button>
      <el-button type="primary" @click="createLead">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="showRedevelopDialog" title="老客二次开发" width="680px">
    <el-form label-position="top">
      <el-form-item label="搜索客户（客户名 / 老板 / 联系人）">
        <el-select
          v-model="redevelopForm.customer_id"
          filterable
          remote
          reserve-keyword
          clearable
          placeholder="输入客户名称或联系人后搜索"
          :remote-method="searchRedevelopCustomers"
          :loading="redevelopSearchLoading"
          style="width: 100%"
        >
          <el-option
            v-for="item in redevelopCustomerOptions"
            :key="`redevelop-customer-${item.id}`"
            :label="`${item.name}（${item.contact_name}）`"
            :value="item.id"
          >
            <div class="redevelop-option">
              <span>{{ item.name }}（{{ item.contact_name }}）</span>
              <el-text type="info" size="small">{{ item.accountant_username }}</el-text>
            </div>
          </el-option>
        </el-select>
      </el-form-item>
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="线索来源">
            <el-input v-model="redevelopForm.source" placeholder="默认：老客户二次开发" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="下次提醒">
            <el-date-picker
              v-model="redevelopForm.next_reminder_at"
              type="date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              :editable="true"
              placeholder="YYYYMMDD 或 YYMMDD"
              @keydown.enter.capture="commitDateInput((v) => (redevelopForm.next_reminder_at = v), $event)"
              @blur.capture="commitDateInput((v) => (redevelopForm.next_reminder_at = v), $event)"
            />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="本次开发需求">
        <el-input
          v-model="redevelopForm.notes"
          type="textarea"
          :rows="3"
          placeholder="例如：新增股权变更服务，预计本周转成交并录入费用"
        />
      </el-form-item>
      <el-text type="info" size="small">
        创建后会生成一条“老客二开线索”，成交时复用原客户，不会重复建客户档案。
      </el-text>
    </el-form>
    <template #footer>
      <el-button @click="showRedevelopDialog = false">取消</el-button>
      <el-button type="primary" :loading="creatingRedevelopLead" @click="createRedevelopLead">
        创建二开线索
      </el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="showFollowupDialog" title="新增跟进" width="520px">
    <el-form label-position="top">
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="跟进日期">
            <el-date-picker
              v-model="followupForm.followup_at"
              type="date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              :editable="true"
              placeholder="YYYYMMDD 或 YYMMDD"
              @keydown.enter.capture="commitDateInput((v) => (followupForm.followup_at = v), $event)"
              @blur.capture="commitDateInput((v) => (followupForm.followup_at = v), $event)"
            />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="下次提醒">
            <el-date-picker
              v-model="followupForm.next_reminder_at"
              type="date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              :editable="true"
              placeholder="YYYYMMDD 或 YYMMDD"
              @keydown.enter.capture="commitDateInput((v) => (followupForm.next_reminder_at = v), $event)"
              @blur.capture="commitDateInput((v) => (followupForm.next_reminder_at = v), $event)"
            />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="跟进反馈">
        <el-input v-model="followupForm.feedback" type="textarea" :rows="3" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="followupForm.notes" type="textarea" :rows="2" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showFollowupDialog = false">取消</el-button>
      <el-button type="primary" @click="submitFollowup">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="showConvertDialog" title="转化并分配会计" width="560px">
    <el-form label-position="top">
      <el-form-item label="线索">
        <el-input :model-value="convertTargetLeadName" disabled />
      </el-form-item>
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="转化后客户名称">
            <el-input v-model="convertForm.customer_name" placeholder="可与线索名称不同" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="转化后联系人">
            <el-input v-model="convertForm.customer_contact_name" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="转化后电话">
        <el-input v-model="convertForm.customer_phone" />
      </el-form-item>
      <el-form-item label="分配会计">
        <el-select v-model="convertForm.accountant_id" placeholder="请选择会计">
          <el-option
            v-for="item in accountantOptions"
            :key="item.id"
            :label="item.username"
            :value="item.id"
          />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showConvertDialog = false">取消</el-button>
      <el-button type="primary" plain :loading="converting" @click="submitConvert">确认转化</el-button>
      <el-button type="primary" :loading="converting" @click="submitConvertAndAddBilling">
        确认转化并添加收费信息
      </el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="showConvertBillingDialog" :title="`添加收费信息 - ${convertBillingTargetName}`" width="760px">
    <el-form label-position="top">
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="序号">
            <el-input-number
              v-model="convertBillingForm.serial_no"
              :min="1"
              :controls="false"
              style="width:100%"
              placeholder="留空自动编号"
            />
          </el-form-item>
        </el-col>
        <el-col :span="16">
          <el-form-item label="客户">
            <el-input :model-value="convertBillingTargetName" disabled />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="6">
          <el-form-item label="收费类别">
            <el-select v-model="convertBillingForm.charge_category">
              <el-option
                v-for="item in chargeCategoryOptions"
                :key="`lead-convert-category-${item}`"
                :label="item"
                :value="item"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="计费方式">
            <el-select v-model="convertBillingForm.charge_mode" @change="onConvertBillingModeChange">
              <el-option
                v-for="item in chargeModeOptions"
                :key="`lead-convert-mode-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="金额口径">
            <el-select v-model="convertBillingForm.amount_basis">
              <el-option
                v-for="item in amountBasisOptions"
                :key="`lead-convert-basis-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="摘要">
            <el-input v-model="convertBillingForm.summary" placeholder="例如：注册服务费" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="6"><el-form-item label="总费用"><el-input-number v-model="convertBillingForm.total_fee" :min="0" :controls="false" style="width:100%" /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="月费用"><el-input-number v-model="convertBillingForm.monthly_fee" :min="0" :controls="false" style="width:100%" /></el-form-item></el-col>
        <el-col :span="6">
          <el-form-item label="开始月份">
            <el-date-picker
              v-model="convertBillingForm.period_start_month"
              type="month"
              format="YYYY-MM"
              value-format="YYYY-MM"
              :disabled="convertBillingForm.charge_mode === 'ONE_TIME'"
              placeholder="YYYY-MM"
              @change="onConvertBillingStartMonthChange"
            />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="结束月份">
            <el-date-picker
              v-model="convertBillingForm.period_end_month"
              type="month"
              format="YYYY-MM"
              value-format="YYYY-MM"
              :disabled="convertBillingForm.charge_mode === 'ONE_TIME'"
              placeholder="YYYY-MM"
            />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="6">
          <el-form-item label="起收日期（精确）">
            <el-date-picker
              v-model="convertBillingForm.collection_start_date"
              type="date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              :editable="true"
              placeholder="YYYYMMDD 或 YYMMDD"
              @keydown.enter.capture="commitDateInput((v) => (convertBillingForm.collection_start_date = v), $event)"
              @blur.capture="commitDateInput((v) => (convertBillingForm.collection_start_date = v), $event)"
            />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="到期日">
            <el-date-picker
              v-model="convertBillingForm.due_month"
              type="date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              :editable="true"
              placeholder="YYYYMMDD 或 YYMMDD"
              @keydown.enter.capture="commitDateInput((v) => (convertBillingForm.due_month = v), $event)"
              @blur.capture="commitDateInput((v) => (convertBillingForm.due_month = v), $event)"
            />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-text type="info" size="small">
            {{ convertBillingForm.charge_mode === "ONE_TIME" ? "按次：默认当天到期" : "按期：默认结束月份=开始月份+11" }}
          </el-text>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="付款方式">
            <el-select v-model="convertBillingForm.payment_method">
              <el-option
                v-for="item in paymentMethodOptions"
                :key="`lead-convert-method-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="台账状态">
            <el-select v-model="convertBillingForm.status">
              <el-option
                v-for="item in billingStatusOptions"
                :key="`lead-convert-status-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8"><el-form-item label="已收金额"><el-input-number v-model="convertBillingForm.received_amount" :min="0" :controls="false" style="width:100%" /></el-form-item></el-col>
      </el-row>
      <el-form-item label="代账周期">
        <el-select v-model="convertBillingForm.billing_cycle_text" placeholder="请选择代账周期">
          <el-option
            v-for="item in billingCycleOptions"
            :key="`lead-convert-cycle-${item}`"
            :label="item"
            :value="item"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="convertBillingForm.note" type="textarea" :rows="2" />
      </el-form-item>
      <el-form-item label="扩展说明">
        <el-input v-model="convertBillingForm.extra_note" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showConvertBillingDialog = false">稍后添加</el-button>
      <el-button type="primary" :loading="creatingConvertBilling" @click="submitConvertBilling">保存收费信息</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="showGuideDialog" title="客户开发流程说明" width="760px">
    <el-space direction="vertical" fill :size="12">
      <el-card shadow="never">
        <template #header>状态说明</template>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="NEW（新线索）">刚录入，尚未有效跟进。</el-descriptions-item>
          <el-descriptions-item label="FOLLOWING（跟进中）">已有跟进记录，正在推进。</el-descriptions-item>
          <el-descriptions-item label="CONVERTED（已转化）">已转客户，进入客户列表与收费流程。</el-descriptions-item>
          <el-descriptions-item label="LOST（已丢失）">当前阶段暂停推进，后续可重新激活。</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card shadow="never">
        <template #header>流程说明</template>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="1. 新增线索">录入开发信息，初始状态 NEW。</el-descriptions-item>
          <el-descriptions-item label="2. 跟进">点击“跟进”记录反馈和下次提醒，进入 FOLLOWING。</el-descriptions-item>
          <el-descriptions-item label="3. 转化">点击“转化”，补充客户档案信息并分配会计。</el-descriptions-item>
          <el-descriptions-item label="4. 客户档案">转化后点“客户档案”进入客户模块页面。</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card shadow="never">
        <template #header>模板筛选说明</template>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="客户跟进模板（FOLLOWUP）">
            适合常规跟进字段：服务方式、收费标准、国家/类型等。
          </el-descriptions-item>
          <el-descriptions-item label="转化模板（CONVERSION）">
            适合转化导向字段：地区、联络时间、备用字段等。
          </el-descriptions-item>
          <el-descriptions-item label="老客二开模板（REDEVELOP）">
            用于老客户二次开发，成交后复用原客户档案并直接录入新增费用。
          </el-descriptions-item>
          <el-descriptions-item label="页面顶部“模板筛选”">
            仅用于过滤列表显示，不会修改线索本身的数据。
          </el-descriptions-item>
        </el-descriptions>
      </el-card>
    </el-space>
    <template #footer>
      <el-button type="primary" @click="showGuideDialog = false">我知道了</el-button>
    </template>
  </el-dialog>

  <el-drawer
    v-model="showHistoryDrawer"
    :title="`跟进历史 - ${historyLeadName}`"
    size="min(760px, 92vw)"
  >
    <el-table v-loading="historyLoading" :data="historyRows" stripe border>
      <el-table-column prop="followup_at" label="跟进日期" width="120" />
      <el-table-column prop="feedback" label="跟进反馈" min-width="180" show-overflow-tooltip />
      <el-table-column
        prop="next_reminder_at"
        label="下次提醒"
        width="120"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        prop="notes"
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
.table-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.redevelop-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

@media (max-width: 900px) {
  .lead-filter-form {
    display: flex;
    flex-wrap: wrap;
  }
}
</style>
