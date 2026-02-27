<script setup lang="ts">
import { ArrowLeft } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { apiClient } from "../api/client";
import type { LeadItem } from "../types";
import { commitDateInput } from "../utils/dateInput";
import { todayInBrowserTimeZone } from "../utils/time";

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

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const followupLoading = ref(false);
const lead = ref<LeadItem | null>(null);
const followups = ref<FollowupItem[]>([]);
const showFollowupDialog = ref(false);

const followupForm = reactive({
  followup_at: todayInBrowserTimeZone(),
  feedback: "",
  notes: "",
  next_reminder_at: null as string | null,
});

function templateLabel(templateType: string) {
  return templateType === "FOLLOWUP" ? "客户跟进模板" : "转化模板";
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
  followupForm.followup_at = todayInBrowserTimeZone();
  followupForm.feedback = "";
  followupForm.notes = "";
  followupForm.next_reminder_at = lead.value?.next_reminder_at ?? null;
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
    ElMessage.success("跟进记录已保存");
    showFollowupDialog.value = false;
    await fetchLeadDetail();
  } catch (error) {
    ElMessage.error("保存跟进失败");
  } finally {
    followupLoading.value = false;
  }
}

function backToLeads() {
  const from = String(route.query.from || "");
  if (from === "customers") {
    router.push("/customers");
    return;
  }
  if (from.startsWith("customer:")) {
    const customerId = Number(from.split(":")[1]);
    if (customerId) {
      router.push(`/customers/${customerId}`);
      return;
    }
  }
  router.push("/leads");
}

onMounted(fetchLeadDetail);
</script>

<template>
  <el-space direction="vertical" fill :size="12">
    <el-card shadow="never">
      <el-space>
        <el-button :icon="ArrowLeft" @click="backToLeads">返回客户开发</el-button>
        <el-button type="primary" :disabled="!lead" @click="openFollowupDialog">新增跟进</el-button>
      </el-space>
    </el-card>

    <el-card v-loading="loading" shadow="never">
      <template #header>
        <div class="head">
          <span>线索详情（总览 -> 明细）</span>
          <el-tag v-if="lead" type="info" effect="plain">{{ templateLabel(lead.template_type) }}</el-tag>
        </div>
      </template>

      <el-empty v-if="!lead" description="未找到线索" />
      <template v-else>
        <el-descriptions :column="3" border>
          <el-descriptions-item label="公司名">{{ lead.name }}</el-descriptions-item>
          <el-descriptions-item label="等级">{{ lead.grade || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ statusLabel(lead.status) }}</el-descriptions-item>
          <el-descriptions-item label="联系人">{{ lead.contact_name }}</el-descriptions-item>
          <el-descriptions-item label="电话">{{ lead.phone }}</el-descriptions-item>
          <el-descriptions-item label="微信">{{ lead.contact_wechat || '-' }}</el-descriptions-item>
          <el-descriptions-item label="传真">{{ lead.fax || '-' }}</el-descriptions-item>
          <el-descriptions-item label="其他联系方式">{{ lead.other_contact || '-' }}</el-descriptions-item>
          <el-descriptions-item label="地区">{{ lead.region || '-' }}</el-descriptions-item>
          <el-descriptions-item label="国家/类型">{{ lead.country || '-' }}</el-descriptions-item>
          <el-descriptions-item label="企业性质">{{ lead.company_nature || '-' }}</el-descriptions-item>
          <el-descriptions-item label="服务方式">{{ lead.service_mode || '-' }}</el-descriptions-item>
          <el-descriptions-item label="服务开始时间">{{ lead.service_start_text || '-' }}</el-descriptions-item>
          <el-descriptions-item label="联络开始时间">{{ lead.contact_start_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="收费标准">{{ lead.fee_standard || '-' }}</el-descriptions-item>
          <el-descriptions-item label="首期账单期间">{{ lead.first_billing_period || '-' }}</el-descriptions-item>
          <el-descriptions-item label="提醒值">{{ lead.reminder_value || '-' }}</el-descriptions-item>
          <el-descriptions-item label="下次提醒">{{ lead.next_reminder_at || '-' }}</el-descriptions-item>
          <el-descriptions-item label="最后跟进日期">{{ lead.last_followup_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="来源">{{ lead.source || '-' }}</el-descriptions-item>
          <el-descriptions-item label="主营/需求" :span="3">{{ lead.main_business || '-' }}</el-descriptions-item>
          <el-descriptions-item label="介绍" :span="3">{{ lead.intro || '-' }}</el-descriptions-item>
          <el-descriptions-item label="备注" :span="3">{{ lead.notes || '-' }}</el-descriptions-item>
        </el-descriptions>
      </template>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="head">
          <span>跟进记录</span>
          <el-tag type="success" effect="plain">{{ followups.length }} 条</el-tag>
        </div>
      </template>
      <el-table :data="followups" stripe border>
        <el-table-column prop="followup_at" label="跟进日期" width="120" />
        <el-table-column prop="feedback" label="跟进反馈" min-width="300" />
        <el-table-column prop="next_reminder_at" label="下次提醒" width="120" />
        <el-table-column prop="notes" label="备注" min-width="220" />
      </el-table>
    </el-card>
  </el-space>

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
      <el-button type="primary" :loading="followupLoading" @click="submitFollowup">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
