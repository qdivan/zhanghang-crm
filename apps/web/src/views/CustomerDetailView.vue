<script setup lang="ts">
import { ArrowDown, ArrowLeft } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { apiClient } from "../api/client";
import FlexibleDateInput from "../components/shared/FlexibleDateInput.vue";
import { useResponsive } from "../composables/useResponsive";
import { useAuthStore } from "../stores/auth";
import type {
  CustomerDetail,
  CustomerTimelineEntry,
  CustomerTimelineEventCreatePayload,
  CustomerTimelineEventUpdatePayload,
  CustomerTimelineSourceType,
} from "../types";
import { todayInBrowserTimeZone } from "../utils/time";
import { leadGradeOptions, leadReminderOptions } from "./lead/viewMeta";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const { isMobile } = useResponsive();
const loading = ref(false);
const timelineSubmitting = ref(false);
const templateApplying = ref(false);
const completeSubmitting = ref(false);
const editLoading = ref(false);
const detail = ref<CustomerDetail | null>(null);
const showTimelineDialog = ref(false);
const showEditDialog = ref(false);
const showCompleteDialog = ref(false);
const detailCollapse = ref<string[]>([]);
const completingTimelineId = ref<number | null>(null);

const canWriteCustomer = computed(() => {
  if (!detail.value || auth.user?.role !== "ACCOUNTANT") return true;
  return detail.value.accountant_username === auth.user.username;
});

const backTarget = computed(() => {
  const from = String(route.query.from || "");
  if (from === "leads") {
    return {
      label: "返回客户开发",
      path: "/leads",
    };
  }
  return {
    label: "返回客户列表",
    path: "/customers",
  };
});

const displayCountry = computed(() => detail.value?.lead.country || detail.value?.lead.region || "-");
const displayServiceStart = computed(
  () => detail.value?.lead.service_start_text || detail.value?.lead.contact_start_date || "-",
);
const displayContactLine = computed(() => {
  if (!detail.value) return "-";
  return [detail.value.contact_name, detail.value.phone].filter(Boolean).join(" / ") || "-";
});

function displayText(value: string | null | undefined) {
  const raw = (value || "").trim();
  return raw || "-";
}

const primaryDesktopFields = computed(() => {
  if (!detail.value) return [];
  return [
    { label: "公司名", value: displayText(detail.value.name), wide: true },
    { label: "等级", value: displayText(detail.value.lead.grade) },
    { label: "国家", value: displayCountry.value },
    { label: "服务开始", value: displayServiceStart.value },
    { label: "对接人及电话", value: displayContactLine.value, wide: true },
    { label: "微信", value: displayText(detail.value.lead.contact_wechat) },
    { label: "最后跟进", value: displayText(detail.value.lead.last_followup_date) },
    { label: "下次提醒", value: displayText(detail.value.lead.next_reminder_at) },
  ];
});

const secondaryDesktopFields = computed(() => {
  if (!detail.value) return [];
  return [
    { label: "企业性质", value: displayText(detail.value.lead.company_nature) },
    { label: "服务方式", value: displayText(detail.value.lead.service_mode) },
    { label: "其他联系人", value: displayText(detail.value.lead.other_contact) },
    { label: "收费标准", value: displayText(detail.value.lead.fee_standard) },
    { label: "首期账单期间", value: displayText(detail.value.lead.first_billing_period) },
    { label: "提醒值", value: displayText(detail.value.lead.reminder_value) },
  ].filter((item) => item.value !== "-");
});

const longDesktopFields = computed(() => {
  if (!detail.value) return [];
  return [
    { label: "主营产品", value: displayText(detail.value.lead.main_business) },
    { label: "介绍人", value: displayText(detail.value.lead.intro) },
    { label: "备注", value: displayText(detail.value.lead.notes) },
  ].filter((item) => item.value !== "-");
});

const timelineForm = reactive<CustomerTimelineEventCreatePayload>({
  occurred_at: todayInBrowserTimeZone(),
  event_type: "COMMUNICATION",
  status: "NOTE",
  reminder_at: null,
  completed_at: null,
  content: "",
  note: "",
  result: "",
  amount: null,
});

const completeForm = reactive<CustomerTimelineEventUpdatePayload>({
  status: "DONE",
  completed_at: todayInBrowserTimeZone(),
  result: "",
  note: "",
});

const editForm = reactive({
  name: "",
  contact_name: "",
  phone: "",
  lead_grade: "",
  lead_country: "",
  lead_service_start_text: "",
  lead_company_nature: "",
  lead_service_mode: "",
  lead_contact_wechat: "",
  lead_other_contact: "",
  lead_fee_standard: "",
  lead_first_billing_period: "",
  lead_reminder_value: "",
  lead_next_reminder_at: null as string | null,
  lead_main_business: "",
  lead_intro: "",
  lead_notes: "",
});

function templateLabel(templateType: string) {
  if (templateType === "FOLLOWUP") return "客户跟进模板";
  if (templateType === "REDEVELOP") return "老客二开模板";
  return "转化模板";
}

function timelineTypeLabel(sourceType: CustomerTimelineSourceType | string) {
  const mapping: Record<string, string> = {
    LEAD_CREATED: "开始开发",
    LEAD_FOLLOWUP: "开发跟进",
    CONVERTED: "客户成单",
    BILLING_RECORD: "收费单",
    BILLING_ACTIVITY: "催收/收款",
    EXECUTION_LOG: "执行进度",
    CUSTOMER_EVENT: "客户记录",
  };
  return mapping[sourceType] ?? sourceType;
}

function timelineTypeTag(sourceType: CustomerTimelineSourceType | string) {
  const mapping: Record<string, "" | "success" | "warning" | "info" | "danger"> = {
    LEAD_CREATED: "info",
    LEAD_FOLLOWUP: "warning",
    CONVERTED: "success",
    BILLING_RECORD: "info",
    BILLING_ACTIVITY: "success",
    EXECUTION_LOG: "warning",
    CUSTOMER_EVENT: "danger",
  };
  return mapping[sourceType] ?? "info";
}

function timelineStatusLabel(statusValue: string) {
  const mapping: Record<string, string> = {
    NOTE: "仅记录",
    OPEN: "待跟进",
    DONE: "已办结",
  };
  return mapping[statusValue] ?? (statusValue || "-");
}

function timelineStatusTag(statusValue: string) {
  const mapping: Record<string, "" | "success" | "warning" | "info"> = {
    NOTE: "info",
    OPEN: "warning",
    DONE: "success",
  };
  return mapping[statusValue] ?? "info";
}

function canCompleteTimeline(item: CustomerTimelineEntry) {
  return canWriteCustomer.value && item.source_type === "CUSTOMER_EVENT" && item.status === "OPEN";
}

async function fetchDetail() {
  const customerId = Number(route.params.id);
  if (!customerId) return;

  loading.value = true;
  try {
    const resp = await apiClient.get<CustomerDetail>(`/customers/${customerId}`);
    detail.value = resp.data;
  } catch (error) {
    ElMessage.error("加载客户档案失败");
  } finally {
    loading.value = false;
  }
}

function goBack() {
  router.push(backTarget.value.path);
}

function openTimelineDialog() {
  if (!detail.value) return;
  if (!canWriteCustomer.value) {
    ElMessage.warning("该客户处于临时只读授权范围，不能新增记录");
    return;
  }
  timelineForm.occurred_at = todayInBrowserTimeZone();
  timelineForm.event_type = "COMMUNICATION";
  timelineForm.status = "NOTE";
  timelineForm.reminder_at = null;
  timelineForm.completed_at = null;
  timelineForm.content = "";
  timelineForm.note = "";
  timelineForm.result = "";
  timelineForm.amount = null;
  showTimelineDialog.value = true;
}

async function submitTimelineEvent() {
  if (!detail.value || !timelineForm.content.trim()) {
    ElMessage.warning("请填写记录内容");
    return;
  }
  if (!canWriteCustomer.value) {
    ElMessage.warning("该客户处于临时只读授权范围，不能新增记录");
    return;
  }

  timelineSubmitting.value = true;
  try {
    await apiClient.post(`/customers/${detail.value.id}/timeline-events`, timelineForm);
    ElMessage.success("客户记录已保存");
    showTimelineDialog.value = false;
    await fetchDetail();
  } catch (error) {
    ElMessage.error("保存失败");
  } finally {
    timelineSubmitting.value = false;
  }
}

async function applyCustomerTemplate(command: string) {
  if (!detail.value || !canWriteCustomer.value) return;
  const templateLabel = command === "hk-company" ? "香港公司模板" : command;
  try {
    await ElMessageBox.confirm(`将为当前客户生成“${templateLabel}”的提醒事项。`, "套用客户模板", {
      type: "warning",
    });
  } catch {
    return;
  }

  templateApplying.value = true;
  try {
    await apiClient.post(`/customers/${detail.value.id}/timeline-templates/${command}`);
    ElMessage.success(`${templateLabel}已套用`);
    await fetchDetail();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || "模板套用失败");
  } finally {
    templateApplying.value = false;
  }
}

function openCompleteDialog(item: CustomerTimelineEntry) {
  if (!detail.value || !canCompleteTimeline(item)) return;
  completingTimelineId.value = item.source_id ?? null;
  completeForm.status = "DONE";
  completeForm.completed_at = todayInBrowserTimeZone();
  completeForm.result = item.result || "";
  completeForm.note = item.note || "";
  showCompleteDialog.value = true;
}

async function submitCompleteTimeline() {
  if (!detail.value || !completingTimelineId.value) return;
  if (!(completeForm.result || "").trim()) {
    ElMessage.warning("请填写办结结果");
    return;
  }

  completeSubmitting.value = true;
  try {
    await apiClient.patch(
      `/customers/${detail.value.id}/timeline-events/${completingTimelineId.value}`,
      completeForm,
    );
    ElMessage.success("客户事项已办结");
    showCompleteDialog.value = false;
    completingTimelineId.value = null;
    await fetchDetail();
  } catch (error) {
    ElMessage.error("办结保存失败");
  } finally {
    completeSubmitting.value = false;
  }
}

function openLeadDetail() {
  if (!detail.value) return;
  router.push({
    path: `/leads/${detail.value.source_lead_id}`,
    query: { from: `customer:${detail.value.id}` },
  });
}

function openEditDialog() {
  if (!detail.value) return;
  if (!canWriteCustomer.value) {
    ElMessage.warning("该客户处于临时只读授权范围，不能编辑档案");
    return;
  }
  editForm.name = detail.value.name;
  editForm.contact_name = detail.value.contact_name;
  editForm.phone = detail.value.phone;
  editForm.lead_grade = detail.value.lead.grade;
  editForm.lead_country = detail.value.lead.country || detail.value.lead.region;
  editForm.lead_service_start_text = detail.value.lead.service_start_text || detail.value.lead.contact_start_date || "";
  editForm.lead_company_nature = detail.value.lead.company_nature;
  editForm.lead_service_mode = detail.value.lead.service_mode;
  editForm.lead_contact_wechat = detail.value.lead.contact_wechat;
  editForm.lead_other_contact = detail.value.lead.other_contact;
  editForm.lead_fee_standard = detail.value.lead.fee_standard;
  editForm.lead_first_billing_period = detail.value.lead.first_billing_period;
  editForm.lead_reminder_value = detail.value.lead.reminder_value;
  editForm.lead_next_reminder_at = detail.value.lead.next_reminder_at;
  editForm.lead_main_business = detail.value.lead.main_business;
  editForm.lead_intro = detail.value.lead.intro;
  editForm.lead_notes = detail.value.lead.notes;
  showEditDialog.value = true;
}

async function submitEdit() {
  if (!detail.value || !editForm.name.trim()) {
    ElMessage.warning("客户名称不能为空");
    return;
  }
  if (!canWriteCustomer.value) {
    ElMessage.warning("该客户处于临时只读授权范围，不能编辑档案");
    return;
  }
  editLoading.value = true;
  try {
    await apiClient.patch(`/customers/${detail.value.id}`, {
      name: editForm.name,
      contact_name: editForm.contact_name,
      phone: editForm.phone,
      lead_grade: editForm.lead_grade,
      lead_country: editForm.lead_country,
      lead_service_start_text: editForm.lead_service_start_text,
      lead_company_nature: editForm.lead_company_nature,
      lead_service_mode: editForm.lead_service_mode,
      lead_contact_wechat: editForm.lead_contact_wechat,
      lead_other_contact: editForm.lead_other_contact,
      lead_fee_standard: editForm.lead_fee_standard,
      lead_first_billing_period: editForm.lead_first_billing_period,
      lead_reminder_value: editForm.lead_reminder_value,
      lead_next_reminder_at: editForm.lead_next_reminder_at,
      lead_main_business: editForm.lead_main_business,
      lead_intro: editForm.lead_intro,
      lead_notes: editForm.lead_notes,
    });
    ElMessage.success("客户档案已更新");
    showEditDialog.value = false;
    await fetchDetail();
  } catch (error) {
    ElMessage.error("保存失败");
  } finally {
    editLoading.value = false;
  }
}

onMounted(fetchDetail);
</script>

<template>
  <el-space direction="vertical" fill :size="12">
    <el-card shadow="never">
      <el-space class="action-bar" wrap>
        <el-button :icon="ArrowLeft" @click="goBack">{{ backTarget.label }}</el-button>
        <el-button :disabled="!detail || !canWriteCustomer" @click="openEditDialog">编辑档案</el-button>
        <el-button type="primary" :disabled="!detail || !canWriteCustomer" @click="openTimelineDialog">
          新增记录
        </el-button>
        <el-dropdown
          :disabled="!detail || !canWriteCustomer || templateApplying"
          @command="applyCustomerTemplate"
        >
          <el-button :loading="templateApplying">
            套用模板
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="hk-company">香港公司模板</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button :disabled="!detail" @click="openLeadDetail">查看开发来源</el-button>
      </el-space>
    </el-card>

    <el-card v-loading="loading" shadow="never">
      <template #header>
        <div class="head">
          <span>客户档案</span>
          <el-space v-if="detail" class="meta-tags" wrap>
            <el-tag type="success" effect="plain">客户ID {{ detail.id }}</el-tag>
            <el-tag type="info" effect="plain">会计 {{ detail.accountant_username }}</el-tag>
            <el-tag effect="plain">{{ templateLabel(detail.lead.template_type) }}</el-tag>
          </el-space>
        </div>
      </template>

      <el-empty v-if="!detail" description="未找到客户" />
      <template v-else>
        <div v-if="isMobile" class="detail-mobile-stack">
          <div class="mobile-record-card">
            <div class="mobile-record-head">
              <div class="mobile-record-main">
                <div class="mobile-record-title">{{ detail.name }}</div>
                <div class="mobile-record-subtitle">
                  会计 {{ detail.accountant_username }} · {{ templateLabel(detail.lead.template_type) }}
                </div>
              </div>
              <el-tag size="small" type="success" effect="plain">客户ID {{ detail.id }}</el-tag>
            </div>
            <div class="mobile-record-metrics">
              <div class="mobile-metric">
                <div class="mobile-metric-label">等级</div>
                <div class="mobile-metric-value">{{ detail.lead.grade || "-" }}</div>
              </div>
              <div class="mobile-metric">
                <div class="mobile-metric-label">国家</div>
                <div class="mobile-metric-value">{{ displayCountry }}</div>
              </div>
              <div class="mobile-metric">
                <div class="mobile-metric-label">服务开始</div>
                <div class="mobile-metric-value">{{ displayServiceStart }}</div>
              </div>
              <div class="mobile-metric">
                <div class="mobile-metric-label">服务方式</div>
                <div class="mobile-metric-value">{{ detail.lead.service_mode || "-" }}</div>
              </div>
              <div class="mobile-metric">
                <div class="mobile-metric-label">对接人</div>
                <div class="mobile-metric-value">{{ displayContactLine }}</div>
              </div>
              <div class="mobile-metric">
                <div class="mobile-metric-label">收费标准</div>
                <div class="mobile-metric-value">{{ detail.lead.fee_standard || "-" }}</div>
              </div>
            </div>
            <div class="detail-long-fields">
              <div class="detail-long-field">
                <div class="detail-long-label">主营产品</div>
                <div class="detail-long-value">{{ detail.lead.main_business || "-" }}</div>
              </div>
              <div class="detail-long-field">
                <div class="detail-long-label">介绍人</div>
                <div class="detail-long-value">{{ detail.lead.intro || "-" }}</div>
              </div>
              <div class="detail-long-field">
                <div class="detail-long-label">备注</div>
                <div class="detail-long-value">{{ detail.lead.notes || "-" }}</div>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="detail-compact-panel">
          <div class="detail-compact-grid">
            <div
              v-for="item in primaryDesktopFields"
              :key="`customer-primary-${item.label}`"
              class="detail-compact-item"
              :class="{ wide: item.wide }"
            >
              <div class="detail-compact-label">{{ item.label }}</div>
              <div class="detail-compact-value">{{ item.value }}</div>
            </div>
          </div>

          <el-collapse v-if="secondaryDesktopFields.length" v-model="detailCollapse" class="detail-secondary-collapse">
            <el-collapse-item name="extra">
              <template #title>
                <span class="detail-collapse-title">补充信息（{{ secondaryDesktopFields.length }}项）</span>
              </template>
              <div class="detail-compact-grid secondary">
                <div
                  v-for="item in secondaryDesktopFields"
                  :key="`customer-secondary-${item.label}`"
                  class="detail-compact-item secondary"
                >
                  <div class="detail-compact-label">{{ item.label }}</div>
                  <div class="detail-compact-value">{{ item.value }}</div>
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>

          <div v-if="longDesktopFields.length" class="detail-long-stack">
            <div
              v-for="item in longDesktopFields"
              :key="`customer-long-${item.label}`"
              class="detail-long-row"
            >
              <div class="detail-long-row-label">{{ item.label }}</div>
              <div class="detail-long-row-value">{{ item.value }}</div>
            </div>
          </div>
        </div>
      </template>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="head">
          <span>客户时间线</span>
          <el-tag type="info" effect="plain">{{ detail?.timeline.length ?? 0 }} 条</el-tag>
        </div>
      </template>
      <div v-if="isMobile" class="mobile-record-list">
        <div v-for="item in detail?.timeline ?? []" :key="`${item.source_type}-${item.source_id ?? item.occurred_at}`" class="mobile-record-card">
          <div class="mobile-record-head">
            <div class="mobile-record-main">
              <div class="mobile-record-title">{{ item.occurred_at }}</div>
              <div class="mobile-record-subtitle">
                {{ timelineTypeLabel(item.source_type) }} · {{ item.actor_username || "系统" }}
              </div>
            </div>
            <el-tag size="small" :type="timelineTypeTag(item.source_type)" effect="plain">
              {{ timelineTypeLabel(item.source_type) }}
            </el-tag>
          </div>
          <div class="detail-long-fields">
            <div class="detail-long-field" v-if="item.status">
              <div class="detail-long-label">状态</div>
              <div class="detail-long-value">
                <el-tag size="small" :type="timelineStatusTag(item.status)" effect="plain">
                  {{ timelineStatusLabel(item.status) }}
                </el-tag>
                <span v-if="item.reminder_at"> · 提醒 {{ item.reminder_at }}</span>
                <span v-if="item.completed_at"> · 办结 {{ item.completed_at }}</span>
              </div>
            </div>
            <div class="detail-long-field">
              <div class="detail-long-label">{{ item.occurred_at }}</div>
              <div class="detail-long-value">{{ item.title }}：{{ item.content || "-" }}</div>
            </div>
            <div v-if="item.result" class="detail-long-field">
              <div class="detail-long-label">跟进结果</div>
              <div class="detail-long-value">{{ item.result }}</div>
            </div>
            <div v-if="item.amount !== null || item.note || item.extra" class="detail-long-field">
              <div class="detail-long-label">补充说明</div>
              <div class="detail-long-value">
                <div v-if="item.amount !== null">金额：{{ item.amount }}</div>
                <div v-if="item.note">{{ item.note }}</div>
                <div v-if="item.extra">{{ item.extra }}</div>
              </div>
            </div>
            <el-button v-if="canCompleteTimeline(item)" size="small" type="primary" plain @click="openCompleteDialog(item)">
              办结
            </el-button>
          </div>
        </div>
      </div>
      <el-table v-else :data="detail?.timeline ?? []" stripe border>
        <el-table-column prop="occurred_at" label="日期" width="120" />
        <el-table-column label="类型" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="timelineTypeTag(row.source_type)" effect="plain">
              {{ timelineTypeLabel(row.source_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="事项" width="130" />
        <el-table-column prop="content" label="内容" min-width="260" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="timelineStatusTag(row.status)" effect="plain">
              {{ timelineStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reminder_at" label="提醒" width="120" />
        <el-table-column prop="completed_at" label="办结" width="120" />
        <el-table-column label="金额" width="100">
          <template #default="{ row }">
            {{ row.amount ?? "-" }}
          </template>
        </el-table-column>
        <el-table-column prop="actor_username" label="记录人" width="110" />
        <el-table-column prop="result" label="结果" min-width="160" show-overflow-tooltip />
        <el-table-column prop="note" label="备注" min-width="180" show-overflow-tooltip />
        <el-table-column prop="extra" label="补充" min-width="160" show-overflow-tooltip />
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button v-if="canCompleteTimeline(row)" link type="primary" @click="openCompleteDialog(row)">
              办结
            </el-button>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </el-space>

  <el-dialog v-model="showTimelineDialog" title="新增客户记录" width="560px">
    <el-form label-position="top">
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="记录日期">
            <FlexibleDateInput v-model="timelineForm.occurred_at" :empty-value="''" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="记录类型">
            <el-select v-model="timelineForm.event_type">
              <el-option label="客户沟通" value="COMMUNICATION" />
              <el-option label="内部讨论" value="MEETING" />
              <el-option label="办理事项" value="DELIVERY" />
              <el-option label="资料/证照" value="DOCUMENT" />
              <el-option label="费用备注" value="FEE_NOTE" />
              <el-option label="其他记录" value="OTHER" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="记录状态">
            <el-select v-model="timelineForm.status">
              <el-option label="仅记录" value="NOTE" />
              <el-option label="待跟进" value="OPEN" />
              <el-option label="已办结" value="DONE" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12" v-if="timelineForm.status === 'OPEN'">
          <el-form-item label="提醒日期">
            <FlexibleDateInput v-model="timelineForm.reminder_at" clearable />
          </el-form-item>
        </el-col>
        <el-col :span="12" v-else-if="timelineForm.status === 'DONE'">
          <el-form-item label="办结日期">
            <FlexibleDateInput v-model="timelineForm.completed_at" clearable />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="记录内容">
        <el-input
          v-model="timelineForm.content"
          type="textarea"
          :rows="3"
          placeholder="例如：收到执照并完成变更、和老板讨论缺发票处理、客户确认补单等"
        />
      </el-form-item>
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="相关金额">
            <el-input-number v-model="timelineForm.amount" :min="0" :precision="2" :controls="false" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="16">
          <el-form-item label="备注">
            <el-input v-model="timelineForm.note" type="textarea" :rows="2" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item v-if="timelineForm.status !== 'NOTE'" label="跟进结果">
        <el-input
          v-model="timelineForm.result"
          type="textarea"
          :rows="2"
          placeholder="已办结时可记录结果；待跟进时可先写计划或注意事项"
        />
      </el-form-item>
      <el-alert
        type="info"
        :closable="false"
        title="这里记录客户成单后的重要事项；待跟进事项可设置提醒日期，办结后可补结果。开发期的联络和开发跟进，请用“查看开发来源”进入线索页查看。"
      />
      <el-text size="small" type="info">
        收款金额请优先在“收费明细”里登记；这里用于补充会议、证照、内部讨论、临时事项等重要记录。
      </el-text>
    </el-form>
    <template #footer>
      <el-button @click="showTimelineDialog = false">取消</el-button>
      <el-button type="primary" :loading="timelineSubmitting" @click="submitTimelineEvent">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="showCompleteDialog" title="办结客户事项" width="520px">
    <el-form label-position="top">
      <el-form-item label="办结日期">
        <FlexibleDateInput v-model="completeForm.completed_at" clearable />
      </el-form-item>
      <el-form-item label="办结结果">
        <el-input
          v-model="completeForm.result"
          type="textarea"
          :rows="3"
          placeholder="例如：已完成香港公司年审，客户已确认资料和费用"
        />
      </el-form-item>
      <el-form-item label="补充备注">
        <el-input v-model="completeForm.note" type="textarea" :rows="2" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showCompleteDialog = false">取消</el-button>
      <el-button type="primary" :loading="completeSubmitting" @click="submitCompleteTimeline">确认办结</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="showEditDialog" title="编辑客户档案" width="760px">
    <el-form label-position="top">
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="公司名">
            <el-input v-model="editForm.name" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="对接人">
            <el-input v-model="editForm.contact_name" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="电话">
            <el-input v-model="editForm.phone" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="等级">
            <el-select v-model="editForm.lead_grade">
              <el-option
                v-for="item in leadGradeOptions"
                :key="`customer-grade-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="国家">
            <el-input v-model="editForm.lead_country" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="服务开始时间">
            <el-input v-model="editForm.lead_service_start_text" placeholder="如 2025.07.02" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="企业性质">
            <el-input v-model="editForm.lead_company_nature" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="服务方式">
            <el-input v-model="editForm.lead_service_mode" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="微信">
            <el-input v-model="editForm.lead_contact_wechat" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="其他联系人">
            <el-input v-model="editForm.lead_other_contact" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="收费标准">
            <el-input v-model="editForm.lead_fee_standard" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="首期账单期间">
            <el-input v-model="editForm.lead_first_billing_period" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="提醒值">
            <el-select v-model="editForm.lead_reminder_value">
              <el-option
                v-for="item in leadReminderOptions"
                :key="`customer-reminder-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="下次提醒">
            <FlexibleDateInput v-model="editForm.lead_next_reminder_at" clearable />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="主营产品">
        <el-input v-model="editForm.lead_main_business" type="textarea" :rows="2" />
      </el-form-item>
      <el-form-item label="介绍人">
        <el-input v-model="editForm.lead_intro" type="textarea" :rows="2" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="editForm.lead_notes" type="textarea" :rows="2" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showEditDialog = false">取消</el-button>
      <el-button type="primary" :loading="editLoading" @click="submitEdit">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.meta-tags {
  justify-content: flex-end;
}

.detail-compact-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.detail-compact-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.detail-compact-item {
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fafbfc;
}

.detail-compact-item.wide {
  grid-column: span 2;
}

.detail-compact-item.secondary {
  background: #ffffff;
}

.detail-compact-label {
  margin-bottom: 4px;
  font-size: 12px;
  line-height: 1.2;
  color: #6b7280;
}

.detail-compact-value {
  font-size: 15px;
  line-height: 1.35;
  color: #111827;
  word-break: break-word;
}

.detail-secondary-collapse {
  border-top: none;
  border-bottom: none;
}

.detail-collapse-title {
  font-size: 13px;
  color: #4b5563;
}

.detail-secondary-collapse :deep(.el-collapse-item__header) {
  height: 34px;
  font-size: 13px;
  color: #4b5563;
}

.detail-secondary-collapse :deep(.el-collapse-item__wrap) {
  border-bottom: none;
}

.detail-secondary-collapse :deep(.el-collapse-item__content) {
  padding-bottom: 4px;
}

.detail-long-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-long-row {
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #ffffff;
}

.detail-long-row-label {
  margin-bottom: 4px;
  font-size: 12px;
  line-height: 1.2;
  color: #6b7280;
}

.detail-long-row-value {
  font-size: 14px;
  line-height: 1.45;
  color: #111827;
  word-break: break-word;
}

@media (max-width: 900px) {
  .head {
    flex-direction: column;
    align-items: flex-start;
  }

  .action-bar {
    width: 100%;
  }

  .detail-mobile-stack {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .detail-long-fields {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-top: 12px;
  }

  .detail-long-field {
    border-top: 1px solid #eef2f7;
    padding-top: 10px;
  }

  .detail-long-label {
    font-size: 12px;
    color: #6b7280;
    margin-bottom: 4px;
  }

  .detail-long-value {
    font-size: 13px;
    line-height: 1.6;
    color: #111827;
    word-break: break-word;
  }
}
</style>
