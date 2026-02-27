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

const auth = useAuthStore();
const router = useRouter();
const loading = ref(false);
const rows = ref<LeadItem[]>([]);
const showLeadDialog = ref(false);
const showFollowupDialog = ref(false);
const showHistoryDrawer = ref(false);
const showConvertDialog = ref(false);
const showGuideDialog = ref(false);
const historyLoading = ref(false);
const historyRows = ref<FollowupItem[]>([]);
const historyLeadName = ref("");
const convertTargetLeadName = ref("");
const accountantOptions = ref<UserLite[]>([]);
const convertForm = reactive({
  lead_id: null as number | null,
  accountant_id: null as number | null,
  customer_name: "",
  customer_contact_name: "",
  customer_phone: "",
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

async function submitConvert() {
  if (!convertForm.lead_id || !convertForm.accountant_id) {
    ElMessage.warning("请先选择分配会计");
    return;
  }
  if (
    !convertForm.customer_name.trim() ||
    !convertForm.customer_contact_name.trim() ||
    !convertForm.customer_phone.trim()
  ) {
    ElMessage.warning("请补充转化后的客户名称、联系人和电话");
    return;
  }
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
    ElMessage.success("已转化为客户");
    showConvertDialog.value = false;
    await fetchLeads();
    router.push(`/customers/${resp.data.customer.id}?from=leads`);
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "转化失败，可能已转化或无权限");
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
      <el-button type="primary" @click="submitConvert">确认转化</el-button>
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

@media (max-width: 900px) {
  .lead-filter-form {
    display: flex;
    flex-wrap: wrap;
  }
}
</style>
