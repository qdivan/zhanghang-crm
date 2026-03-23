<script setup lang="ts">
import { ArrowLeft } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { apiClient } from "../api/client";
import FlexibleDateInput from "../components/shared/FlexibleDateInput.vue";
import { useResponsive } from "../composables/useResponsive";
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
const backTarget = computed(() => {
  const from = String(route.query.from || "");
  if (from === "customers") {
    return {
      label: "返回客户列表",
      to: "/customers",
    };
  }
  if (from.startsWith("customer:")) {
    const customerId = Number(from.split(":")[1]);
    if (customerId) {
      return {
        label: "返回客户档案",
        to: `/customers/${customerId}`,
      };
    }
  }
  return {
    label: "返回客户开发",
    to: "/leads",
  };
});

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
  <el-space direction="vertical" fill :size="12">
    <el-card shadow="never">
      <el-space class="action-bar" wrap>
        <el-button :icon="ArrowLeft" @click="backToLeads">{{ backTarget.label }}</el-button>
        <el-button type="primary" :disabled="!lead" @click="openFollowupDialog">新增开发跟进</el-button>
      </el-space>
    </el-card>

    <el-card v-loading="loading" shadow="never">
      <template #header>
        <div class="head">
          <span>{{ isMobile ? "线索详情" : "线索详情（对齐 Excel 明细页）" }}</span>
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
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
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
