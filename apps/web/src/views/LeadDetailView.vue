<script setup lang="ts">
import { ArrowLeft, MoreFilled } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { apiClient } from "../api/client";
import MobileActionSheet from "../components/mobile/MobileActionSheet.vue";
import FlexibleDateInput from "../components/shared/FlexibleDateInput.vue";
import { useResponsive } from "../composables/useResponsive";
import { isMobileAppPath } from "../mobile/config";
import type { LeadItem } from "../types";
import { todayInBrowserTimeZone } from "../utils/time";
import { buildNextReminderDate, getDefaultReminderValueForGrade, leadGradeOptions, leadReminderOptions } from "./lead/viewMeta";

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

const route = useRoute();
const router = useRouter();
const { isMobile } = useResponsive();
const loading = ref(false);
const followupLoading = ref(false);
const lead = ref<LeadItem | null>(null);
const followups = ref<FollowupItem[]>([]);
const showFollowupDialog = ref(false);
const showMobileSecondaryActionSheet = ref(false);
const isMobileWorkflow = computed(() => isMobileAppPath(route.path));
const backTarget = computed(() => {
  const from = String(route.query.from || "");
  if (from === "customers") {
    return {
      label: "返回客户列表",
      to: isMobileWorkflow.value ? "/m/customers" : "/customers",
    };
  }
  if (from.startsWith("customer:")) {
    const customerId = Number(from.split(":")[1]);
    if (customerId) {
      return {
        label: "返回客户档案",
        to: `${isMobileWorkflow.value ? "/m/customers" : "/customers"}/${customerId}`,
      };
    }
  }
  return {
    label: "返回客户开发",
    to: isMobileWorkflow.value ? "/m/leads" : "/leads",
  };
});

const leadAreaLabel = computed(() => (lead.value?.template_type === "FOLLOWUP" ? "国家" : "地区"));
const leadAreaValue = computed(() => {
  if (!lead.value) return "-";
  return lead.value.template_type === "FOLLOWUP" ? (lead.value.country || "-") : (lead.value.region || "-");
});
const leadStartLabel = computed(() => (lead.value?.template_type === "FOLLOWUP" ? "服务开始" : "联络开始"));
const leadStartValue = computed(() => {
  if (!lead.value) return "-";
  return lead.value.template_type === "FOLLOWUP"
    ? (lead.value.service_start_text || "-")
    : (lead.value.contact_start_date || "-");
});
const leadContactLine = computed(() => {
  if (!lead.value) return "-";
  if (lead.value.template_type === "FOLLOWUP") {
    return [lead.value.contact_name, lead.value.contact_wechat].filter(Boolean).join(" / ") || "-";
  }
  return lead.value.contact_wechat
    ? `${lead.value.contact_name} / ${lead.value.contact_wechat}`
    : (lead.value.contact_name || "-");
});
const leadHeroCopy = computed(() => {
  if (!lead.value) return "线索摘要、提醒和跟进记录都在同一页内查看。";
  return `${statusLabel(lead.value.status)} · ${leadContactLine.value}`;
});
const leadFocusMeta = computed(() => {
  if (!lead.value) return [];
  return [
    lead.value.phone ? `电话 ${lead.value.phone}` : "电话 -",
    lead.value.next_reminder_at ? `提醒 ${lead.value.next_reminder_at}` : `提醒值 ${lead.value.reminder_value || "-"}`,
  ];
});
const leadSignalFacts = computed(() => {
  if (!lead.value) return [];
  return [
    { label: "等级", value: lead.value.grade || "-" },
    { label: leadAreaLabel.value, value: leadAreaValue.value },
    { label: leadStartLabel.value, value: leadStartValue.value },
    { label: "提醒值", value: lead.value.reminder_value || "-" },
  ];
});
const leadSummaryHighlights = computed(() => {
  if (!lead.value) return [];
  return [
    { label: "联系人", value: leadContactLine.value },
    { label: "下次提醒", value: lead.value.next_reminder_at || "待设置" },
    { label: "主营", value: lead.value.main_business || "待补充", wide: true },
  ];
});
const leadSummaryNotes = computed(() => {
  if (!lead.value) return [];
  return [
    { label: "介绍人", value: lead.value.intro || "未补充" },
    { label: "备注", value: lead.value.notes || "未补充", multiline: true },
  ];
});
const mobileSecondaryActionItems = computed(() =>
  [
    lead.value?.customer_id
      ? {
          key: "customer",
          label: "客户档案",
          description: "跳转到这条线索已转化的客户档案。",
        }
      : null,
    lead.value?.phone
      ? {
          key: "copy-phone",
          label: "复制电话",
          description: "把联系电话复制到剪贴板。",
        }
      : null,
    lead.value?.contact_wechat
      ? {
          key: "copy-wechat",
          label: "复制微信",
          description: "把微信号复制到剪贴板。",
        }
      : null,
  ].filter(Boolean) as Array<{ key: string; label: string; description: string }>,
);
const hasMobileSecondaryActions = computed(() => mobileSecondaryActionItems.value.length > 0);

const followupForm = reactive({
  followup_at: todayInBrowserTimeZone(),
  grade: "",
  reminder_value: "",
  feedback: "",
  notes: "",
  next_reminder_at: null as string | null,
});

function templateLabel(templateType: string) {
  if (templateType === "FOLLOWUP") return "客户跟进模板";
  if (templateType === "REDEVELOP") return "老客二开模板";
  return "转化模板";
}

function statusLabel(status: string) {
  if (status === "NEW") return "新线索";
  if (status === "FOLLOWING") return "跟进中";
  if (status === "CONVERTED") return "已转化";
  if (status === "LOST") return "已丢失";
  return status;
}

async function fetchLeadDetail() {
  const leadId = Number(route.params.id);
  if (!leadId) return;

  loading.value = true;
  try {
    const [leadResp, followupResp] = await Promise.all([
      apiClient.get<LeadItem>(`/leads/${leadId}`),
      apiClient.get<FollowupItem[]>(`/leads/${leadId}/followups`),
    ]);
    lead.value = leadResp.data;
    followups.value = followupResp.data;
  } catch (error) {
    ElMessage.error("加载线索详情失败");
  } finally {
    loading.value = false;
  }
}

function openFollowupDialog() {
  const grade = lead.value?.grade || "意向中";
  followupForm.followup_at = todayInBrowserTimeZone();
  followupForm.grade = grade;
  followupForm.reminder_value = lead.value?.reminder_value || getDefaultReminderValueForGrade(grade);
  followupForm.feedback = "";
  followupForm.notes = "";
  followupForm.next_reminder_at =
    lead.value?.next_reminder_at ?? buildNextReminderDate(followupForm.followup_at, followupForm.reminder_value);
  showFollowupDialog.value = true;
}

async function submitFollowup() {
  const leadId = Number(route.params.id);
  if (!leadId || !followupForm.feedback.trim()) {
    ElMessage.warning("请填写跟进反馈");
    return;
  }

  followupLoading.value = true;
  try {
    await apiClient.post(`/leads/${leadId}/followups`, followupForm);
    ElMessage.success("开发跟进已保存");
    showFollowupDialog.value = false;
    await fetchLeadDetail();
  } catch (error) {
    ElMessage.error("保存跟进失败");
  } finally {
    followupLoading.value = false;
  }
}

function backToLeads() {
  router.push(backTarget.value.to);
}

function openCustomerArchive() {
  if (!lead.value?.customer_id) return;
  router.push({
    path: `${isMobileWorkflow.value ? "/m/customers" : "/customers"}/${lead.value.customer_id}`,
    query: { from: "leads" },
  });
}

async function copyText(label: string, value: string | null | undefined) {
  const text = (value || "").trim();
  if (!text) {
    ElMessage.warning(`当前没有${label}`);
    return;
  }

  try {
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
    } else if (typeof document !== "undefined") {
      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.setAttribute("readonly", "true");
      textarea.style.position = "absolute";
      textarea.style.left = "-9999px";
      document.body.appendChild(textarea);
      textarea.select();
      const copied = (document as Document & { execCommand?: (command: string) => boolean }).execCommand?.("copy");
      document.body.removeChild(textarea);
      if (!copied) {
        throw new Error("copy failed");
      }
    } else {
      throw new Error("clipboard unavailable");
    }
    ElMessage.success(`${label}已复制`);
  } catch (error) {
    ElMessage.error(`复制${label}失败`);
  }
}

async function handleMobileSecondaryActionSelect(action: string) {
  if (action === "customer") {
    openCustomerArchive();
    return;
  }
  if (action === "copy-phone") {
    await copyText("电话", lead.value?.phone);
    return;
  }
  if (action === "copy-wechat") {
    await copyText("微信", lead.value?.contact_wechat);
  }
}

function syncReminderFromGrade() {
  const reminderValue = getDefaultReminderValueForGrade(followupForm.grade);
  if (reminderValue) {
    followupForm.reminder_value = reminderValue;
    followupForm.next_reminder_at = buildNextReminderDate(followupForm.followup_at, reminderValue);
  }
}

function syncReminderDate() {
  followupForm.next_reminder_at = buildNextReminderDate(followupForm.followup_at, followupForm.reminder_value);
}

watch(
  () => followupForm.grade,
  () => {
    if (!showFollowupDialog.value) return;
    syncReminderFromGrade();
  },
);

watch(
  [() => followupForm.followup_at, () => followupForm.reminder_value],
  () => {
    if (!showFollowupDialog.value) return;
    syncReminderDate();
  },
);

onMounted(fetchLeadDetail);
</script>

<template>
  <template v-if="isMobileWorkflow">
    <section class="mobile-page lead-detail-mobile-page">
      <section class="mobile-shell-panel">
        <div class="lead-detail-mobile-hero">
          <div>
            <div class="lead-detail-mobile-eyebrow">{{ lead ? templateLabel(lead.template_type) : "开发详情" }}</div>
            <div class="lead-detail-mobile-title">{{ lead?.name || "开发详情" }}</div>
            <div class="lead-detail-mobile-copy">{{ leadHeroCopy }}</div>
          </div>
          <div class="lead-detail-mobile-hero-actions">
            <el-button class="mobile-row-primary-button" type="primary" :disabled="!lead" @click="openFollowupDialog">
              新增开发跟进
            </el-button>
            <el-button
              v-if="hasMobileSecondaryActions"
              class="mobile-row-secondary-button"
              plain
              @click="showMobileSecondaryActionSheet = true"
            >
              更多操作
              <el-icon class="el-icon--right"><MoreFilled /></el-icon>
            </el-button>
          </div>
        </div>
        <div v-if="lead" class="lead-detail-mobile-summary-card">
          <div class="lead-detail-mobile-summary-head">
            <div class="lead-detail-mobile-summary-main">
              <span class="lead-detail-mobile-summary-kicker">当前状态</span>
              <strong>{{ statusLabel(lead.status) }}</strong>
              <div class="lead-detail-mobile-summary-copy">{{ leadContactLine }}</div>
            </div>
            <el-tag
              class="mobile-status-tag"
              size="small"
              effect="plain"
              :type="lead.next_reminder_at ? 'warning' : 'info'"
            >
              {{ lead.next_reminder_at || "无提醒" }}
            </el-tag>
          </div>
          <div class="lead-detail-mobile-summary-meta">
            <span v-for="item in leadFocusMeta" :key="item">{{ item }}</span>
          </div>
          <div class="lead-detail-mobile-signal-grid">
            <article v-for="item in leadSignalFacts" :key="item.label" class="lead-detail-mobile-signal">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </article>
          </div>
        </div>
      </section>

      <section class="mobile-shell-panel" v-loading="loading">
        <div class="lead-detail-mobile-section-head">
          <div class="lead-detail-mobile-section-title">线索摘要</div>
          <div class="lead-detail-mobile-section-copy">先看判断线索和下一步动作需要的关键信息。</div>
        </div>
        <div v-if="!lead" class="mobile-empty-block">
          <div class="mobile-empty-kicker">线索信息</div>
          <div class="mobile-empty-title">未找到线索</div>
          <div class="mobile-empty-copy">返回开发列表重新选择线索，或检查当前跳转路径。</div>
        </div>
        <template v-else>
          <div class="lead-detail-mobile-summary-grid">
            <div
              v-for="item in leadSummaryHighlights"
              :key="item.label"
              class="lead-detail-mobile-summary-tile"
              :class="{ wide: item.wide }"
            >
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
          </div>
          <div v-if="leadSummaryNotes.length" class="lead-detail-mobile-note-stack">
            <article
              v-for="item in leadSummaryNotes"
              :key="item.label"
              class="lead-detail-mobile-note-card"
              :class="{ multiline: item.multiline }"
            >
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </article>
          </div>
        </template>
      </section>

      <section class="mobile-shell-panel">
        <div class="lead-detail-mobile-section-head">
          <div class="lead-detail-mobile-section-title">开发跟进记录</div>
          <el-tag class="mobile-count-tag" size="small" effect="plain">{{ followups.length }} 条</el-tag>
        </div>
        <div v-if="!followups.length" class="mobile-empty-block">
          <div class="mobile-empty-kicker">开发跟进记录</div>
          <div class="mobile-empty-title">还没有开发跟进记录</div>
          <div class="mobile-empty-copy">先补一条跟进，后续提醒和进展会在这里连续累积。</div>
        </div>
        <div v-else class="lead-detail-mobile-timeline">
          <article v-for="item in followups" :key="item.id" class="lead-detail-mobile-entry">
            <div class="lead-detail-mobile-entry-head">
              <div>
                <strong>{{ item.followup_at }}</strong>
                <div class="lead-detail-mobile-entry-copy">记录人 {{ item.created_by_username || "-" }}</div>
              </div>
              <el-tag class="mobile-status-tag" size="small" effect="plain" :type="item.next_reminder_at ? 'warning' : 'info'">
                {{ item.next_reminder_at || "无提醒" }}
              </el-tag>
            </div>
            <div class="lead-detail-mobile-entry-body">{{ item.feedback || "-" }}</div>
            <div v-if="item.notes" class="lead-detail-mobile-entry-meta">备注 {{ item.notes }}</div>
          </article>
        </div>
      </section>
    </section>

    <MobileActionSheet
      v-model="showMobileSecondaryActionSheet"
      title="线索更多操作"
      :subtitle="lead?.name || ''"
      :items="mobileSecondaryActionItems"
      @select="handleMobileSecondaryActionSelect"
    />
  </template>

  <el-space v-else direction="vertical" fill :size="12">
    <el-card shadow="never">
      <el-space class="action-bar" wrap>
        <el-button :icon="ArrowLeft" @click="backToLeads">{{ backTarget.label }}</el-button>
        <el-button type="primary" :disabled="!lead" @click="openFollowupDialog">新增开发跟进</el-button>
      </el-space>
    </el-card>

    <el-card v-loading="loading" shadow="never">
      <template #header>
        <div class="head">
          <span>开发来源</span>
          <el-space v-if="lead">
            <el-tag type="info" effect="plain">{{ templateLabel(lead.template_type) }}</el-tag>
            <el-tag effect="plain">{{ statusLabel(lead.status) }}</el-tag>
          </el-space>
        </div>
      </template>

      <el-empty v-if="!lead" description="未找到线索" />
      <template v-else>
        <div v-if="isMobile" class="detail-mobile-stack">
          <div class="mobile-record-card">
            <div class="mobile-record-head">
              <div class="mobile-record-main">
                <div class="mobile-record-title">{{ lead.name }}</div>
                <div class="mobile-record-subtitle">
                  {{ templateLabel(lead.template_type) }} · {{ statusLabel(lead.status) }}
                </div>
              </div>
            </div>
            <div class="mobile-record-metrics">
              <div class="mobile-metric">
                <div class="mobile-metric-label">等级</div>
                <div class="mobile-metric-value">{{ lead.grade || "-" }}</div>
              </div>
              <div class="mobile-metric">
                <div class="mobile-metric-label">{{ lead.template_type === "FOLLOWUP" ? "国家" : "地区" }}</div>
                <div class="mobile-metric-value">{{ lead.template_type === "FOLLOWUP" ? (lead.country || "-") : (lead.region || "-") }}</div>
              </div>
              <div class="mobile-metric">
                <div class="mobile-metric-label">{{ lead.template_type === "FOLLOWUP" ? "服务开始" : "联络开始" }}</div>
                <div class="mobile-metric-value">
                  {{ lead.template_type === "FOLLOWUP" ? (lead.service_start_text || "-") : (lead.contact_start_date || "-") }}
                </div>
              </div>
              <div class="mobile-metric">
                <div class="mobile-metric-label">电话</div>
                <div class="mobile-metric-value">{{ lead.phone || "-" }}</div>
              </div>
              <div class="mobile-metric">
                <div class="mobile-metric-label">联系人</div>
                <div class="mobile-metric-value">
                  {{
                    lead.template_type === "FOLLOWUP"
                      ? [lead.contact_name, lead.contact_wechat].filter(Boolean).join(" / ") || "-"
                      : (lead.contact_wechat ? `${lead.contact_name} / ${lead.contact_wechat}` : lead.contact_name || "-")
                  }}
                </div>
              </div>
              <div class="mobile-metric">
                <div class="mobile-metric-label">下次提醒</div>
                <div class="mobile-metric-value">{{ lead.next_reminder_at || "-" }}</div>
              </div>
            </div>
            <div class="detail-long-fields">
              <div class="detail-long-field">
                <div class="detail-long-label">主营</div>
                <div class="detail-long-value">{{ lead.main_business || "-" }}</div>
              </div>
              <div class="detail-long-field">
                <div class="detail-long-label">介绍人</div>
                <div class="detail-long-value">{{ lead.intro || "-" }}</div>
              </div>
              <div class="detail-long-field">
                <div class="detail-long-label">备注</div>
                <div class="detail-long-value">{{ lead.notes || "-" }}</div>
              </div>
            </div>
          </div>
        </div>
        <el-descriptions v-else-if="lead.template_type === 'FOLLOWUP'" :column="2" border>
          <el-descriptions-item label="公司名">{{ lead.name }}</el-descriptions-item>
          <el-descriptions-item label="等级">{{ lead.grade || '-' }}</el-descriptions-item>
          <el-descriptions-item label="国家">{{ lead.country || '-' }}</el-descriptions-item>
          <el-descriptions-item label="服务开始时间">{{ lead.service_start_text || '-' }}</el-descriptions-item>
          <el-descriptions-item label="企业性质">{{ lead.company_nature || '-' }}</el-descriptions-item>
          <el-descriptions-item label="服务方式">{{ lead.service_mode || '-' }}</el-descriptions-item>
          <el-descriptions-item label="对接人及电话">
            {{ [lead.contact_name, lead.phone].filter(Boolean).join(' / ') || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="微信">{{ lead.contact_wechat || '-' }}</el-descriptions-item>
          <el-descriptions-item label="其他联系人">{{ lead.other_contact || '-' }}</el-descriptions-item>
          <el-descriptions-item label="收费标准">{{ lead.fee_standard || '-' }}</el-descriptions-item>
          <el-descriptions-item label="首期账单期间">{{ lead.first_billing_period || '-' }}</el-descriptions-item>
          <el-descriptions-item label="最后跟进日期">{{ lead.last_followup_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="提醒值">{{ lead.reminder_value || '-' }}</el-descriptions-item>
          <el-descriptions-item label="下次提醒">{{ lead.next_reminder_at || '-' }}</el-descriptions-item>
          <el-descriptions-item label="主营产品" :span="2">{{ lead.main_business || '-' }}</el-descriptions-item>
          <el-descriptions-item label="介绍人" :span="2">{{ lead.intro || '-' }}</el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">{{ lead.notes || '-' }}</el-descriptions-item>
        </el-descriptions>
        <el-descriptions v-else :column="2" border>
          <el-descriptions-item label="公司名">{{ lead.name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="等级">{{ lead.grade || '-' }}</el-descriptions-item>
          <el-descriptions-item label="地区">{{ lead.region || '-' }}</el-descriptions-item>
          <el-descriptions-item label="联络开始时间">{{ lead.contact_start_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="联系人（微信号）">
            {{ lead.contact_wechat ? `${lead.contact_name} / ${lead.contact_wechat}` : lead.contact_name || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="电话">{{ lead.phone || '-' }}</el-descriptions-item>
          <el-descriptions-item label="其他联系方式">{{ lead.other_contact || '-' }}</el-descriptions-item>
          <el-descriptions-item label="备注">{{ lead.notes || '-' }}</el-descriptions-item>
          <el-descriptions-item label="介绍人">{{ lead.intro || '-' }}</el-descriptions-item>
          <el-descriptions-item label="主营" :span="2">{{ lead.main_business || '-' }}</el-descriptions-item>
          <el-descriptions-item label="备用2">{{ lead.reserve_2 || '-' }}</el-descriptions-item>
          <el-descriptions-item label="备用3">{{ lead.reserve_3 || '-' }}</el-descriptions-item>
          <el-descriptions-item label="备用4">{{ lead.reserve_4 || '-' }}</el-descriptions-item>
          <el-descriptions-item label="最后跟进日期">{{ lead.last_followup_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="提醒值">{{ lead.reminder_value || '-' }}</el-descriptions-item>
          <el-descriptions-item label="下次提醒">{{ lead.next_reminder_at || '-' }}</el-descriptions-item>
        </el-descriptions>
      </template>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="head">
          <span>开发跟进记录</span>
          <el-tag type="success" effect="plain">{{ followups.length }} 条</el-tag>
        </div>
      </template>
      <div v-if="isMobile" class="mobile-record-list">
        <div v-for="item in followups" :key="item.id" class="mobile-record-card">
          <div class="mobile-record-head">
            <div class="mobile-record-main">
              <div class="mobile-record-title">{{ item.followup_at }}</div>
              <div class="mobile-record-subtitle">
                记录人：{{ item.created_by_username || "-" }} · 下次提醒：{{ item.next_reminder_at || "-" }}
              </div>
            </div>
          </div>
          <div class="detail-long-fields">
            <div class="detail-long-field">
              <div class="detail-long-label">跟进反馈</div>
              <div class="detail-long-value">{{ item.feedback || "-" }}</div>
            </div>
            <div class="detail-long-field">
              <div class="detail-long-label">备注</div>
              <div class="detail-long-value">{{ item.notes || "-" }}</div>
            </div>
          </div>
        </div>
      </div>
      <el-table v-else :data="followups" stripe border>
        <el-table-column prop="followup_at" label="跟进日期" width="120" />
        <el-table-column prop="feedback" label="跟进反馈" min-width="300" />
        <el-table-column prop="next_reminder_at" label="下次提醒" width="120" />
        <el-table-column prop="created_by_username" label="记录人" width="110" />
        <el-table-column prop="notes" label="备注" min-width="220" />
      </el-table>
    </el-card>
  </el-space>

  <el-dialog v-model="showFollowupDialog" title="新增开发跟进" width="720px">
    <el-form label-position="top">
      <el-row :gutter="12">
        <el-col :span="6">
          <el-form-item label="跟进日期">
            <FlexibleDateInput v-model="followupForm.followup_at" :empty-value="''" />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="等级">
            <el-select v-model="followupForm.grade" @change="syncReminderFromGrade">
              <el-option
                v-for="item in leadGradeOptions"
                :key="`lead-detail-grade-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="提醒值">
            <el-select v-model="followupForm.reminder_value" @change="syncReminderDate">
              <el-option
                v-for="item in leadReminderOptions"
                :key="`lead-detail-reminder-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="下次提醒">
            <FlexibleDateInput v-model="followupForm.next_reminder_at" clearable />
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
      <el-button type="primary" :loading="followupLoading" @click="submitFollowup">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.lead-detail-mobile-page {
  gap: 12px;
}

.lead-detail-mobile-hero,
.lead-detail-mobile-section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.lead-detail-mobile-eyebrow {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--app-text-muted);
}

.lead-detail-mobile-title,
.lead-detail-mobile-section-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.lead-detail-mobile-copy {
  margin-top: 3px;
  font-size: 12px;
  color: var(--app-text-muted);
}

.lead-detail-mobile-section-copy {
  max-width: 220px;
  font-size: 11px;
  line-height: 1.45;
  text-align: right;
  color: var(--app-text-muted);
}

.lead-detail-mobile-hero-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.lead-detail-mobile-summary-card {
  margin-top: 12px;
  padding: 14px;
  border: 1px solid rgba(77, 128, 150, 0.18);
  background:
    linear-gradient(135deg, rgba(77, 128, 150, 0.14), rgba(255, 255, 255, 0.96)),
    var(--app-bg-soft);
}

.lead-detail-mobile-summary-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.lead-detail-mobile-summary-main {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  flex: 1;
}

.lead-detail-mobile-summary-kicker,
.lead-detail-mobile-signal span,
.lead-detail-mobile-summary-tile span,
.lead-detail-mobile-note-card span {
  font-size: 11px;
  color: var(--app-text-muted);
}

.lead-detail-mobile-summary-main strong {
  font-size: 30px;
  line-height: 0.95;
  color: var(--app-text-primary);
}

.lead-detail-mobile-summary-copy {
  font-size: 13px;
  line-height: 1.45;
  color: var(--app-text-secondary);
}

.lead-detail-mobile-summary-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  margin-top: 12px;
  font-size: 12px;
  color: var(--app-text-muted);
}

.lead-detail-mobile-signal-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
}

.lead-detail-mobile-signal {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 9px 10px;
  border: 1px solid var(--app-border-soft);
  background: var(--app-bg-soft);
}

.lead-detail-mobile-signal strong,
.lead-detail-mobile-summary-tile strong,
.lead-detail-mobile-note-card strong {
  font-size: 13px;
  line-height: 1.45;
  color: var(--app-text-primary);
}

.lead-detail-mobile-summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 12px;
}

.lead-detail-mobile-summary-tile {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px;
  border: 1px solid var(--app-border-soft);
  background: var(--app-bg-soft);
}

.lead-detail-mobile-summary-tile.wide {
  grid-column: span 2;
}

.lead-detail-mobile-note-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
}

.lead-detail-mobile-note-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 0 0;
  border-top: 1px solid var(--app-border-soft);
}

.lead-detail-mobile-note-card.multiline strong {
  line-height: 1.6;
}

.lead-detail-mobile-timeline {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.lead-detail-mobile-entry {
  border-top: 1px solid var(--app-border-soft);
  padding-top: 12px;
}

.lead-detail-mobile-entry:first-child {
  border-top: none;
  padding-top: 0;
}

.lead-detail-mobile-entry-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.lead-detail-mobile-entry-head strong {
  font-size: 14px;
  color: var(--app-text-primary);
}

.lead-detail-mobile-entry-head span,
.lead-detail-mobile-entry-copy,
.lead-detail-mobile-entry-meta {
  font-size: 12px;
  color: var(--app-text-muted);
}

.lead-detail-mobile-entry-body {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--app-text-secondary);
}

.lead-detail-mobile-entry-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 8px;
}

.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

@media (max-width: 768px) {
  .lead-detail-mobile-hero {
    flex-direction: column;
  }

  .lead-detail-mobile-hero-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .lead-detail-mobile-signal-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .lead-detail-mobile-section-head,
  .lead-detail-mobile-summary-head {
    flex-direction: column;
  }

  .lead-detail-mobile-section-copy {
    max-width: none;
    text-align: left;
  }

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

  .lead-detail-mobile-summary-grid {
    grid-template-columns: 1fr;
  }

  .lead-detail-mobile-summary-tile.wide {
    grid-column: span 1;
  }
}

@media (max-width: 420px) {
  .lead-detail-mobile-signal-grid {
    grid-template-columns: 1fr;
  }
}
</style>
