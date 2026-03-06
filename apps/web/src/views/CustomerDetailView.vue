<script setup lang="ts">
import { ArrowLeft } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { apiClient } from "../api/client";
import { useAuthStore } from "../stores/auth";
import type { CustomerDetail } from "../types";
import { commitDateInput } from "../utils/dateInput";
import { todayInBrowserTimeZone } from "../utils/time";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const loading = ref(false);
const followupLoading = ref(false);
const editLoading = ref(false);
const detail = ref<CustomerDetail | null>(null);
const showFollowupDialog = ref(false);
const showEditDialog = ref(false);

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

const followupForm = reactive({
  followup_at: todayInBrowserTimeZone(),
  feedback: "",
  notes: "",
  next_reminder_at: null as string | null,
});

const editForm = reactive({
  name: "",
  contact_name: "",
  phone: "",
  lead_grade: "",
  lead_contact_wechat: "",
  lead_fax: "",
  lead_other_contact: "",
  lead_region: "",
  lead_country: "",
  lead_service_start_text: "",
  lead_company_nature: "",
  lead_service_mode: "",
  lead_fee_standard: "",
  lead_first_billing_period: "",
  lead_reminder_value: "",
  lead_next_reminder_at: null as string | null,
  lead_source: "",
  lead_main_business: "",
  lead_intro: "",
  lead_notes: "",
});

function templateLabel(templateType: string) {
  if (templateType === "FOLLOWUP") return "客户跟进模板";
  if (templateType === "REDEVELOP") return "老客二开模板";
  return "转化模板";
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

function openFollowupDialog() {
  if (!detail.value) return;
  if (!canWriteCustomer.value) {
    ElMessage.warning("该客户处于临时只读授权范围，不能新增跟进");
    return;
  }
  followupForm.followup_at = todayInBrowserTimeZone();
  followupForm.feedback = "";
  followupForm.notes = "";
  followupForm.next_reminder_at = detail.value.lead.next_reminder_at;
  showFollowupDialog.value = true;
}

async function submitFollowup() {
  if (!detail.value || !followupForm.feedback.trim()) {
    ElMessage.warning("请填写跟进反馈");
    return;
  }
  if (!canWriteCustomer.value) {
    ElMessage.warning("该客户处于临时只读授权范围，不能新增跟进");
    return;
  }

  followupLoading.value = true;
  try {
    await apiClient.post(`/leads/${detail.value.source_lead_id}/followups`, followupForm);
    ElMessage.success("客户跟进已保存");
    showFollowupDialog.value = false;
    await fetchDetail();
  } catch (error) {
    ElMessage.error("保存失败");
  } finally {
    followupLoading.value = false;
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
  editForm.lead_contact_wechat = detail.value.lead.contact_wechat;
  editForm.lead_fax = detail.value.lead.fax;
  editForm.lead_other_contact = detail.value.lead.other_contact;
  editForm.lead_region = detail.value.lead.region;
  editForm.lead_country = detail.value.lead.country;
  editForm.lead_service_start_text = detail.value.lead.service_start_text;
  editForm.lead_company_nature = detail.value.lead.company_nature;
  editForm.lead_service_mode = detail.value.lead.service_mode;
  editForm.lead_fee_standard = detail.value.lead.fee_standard;
  editForm.lead_first_billing_period = detail.value.lead.first_billing_period;
  editForm.lead_reminder_value = detail.value.lead.reminder_value;
  editForm.lead_next_reminder_at = detail.value.lead.next_reminder_at;
  editForm.lead_source = detail.value.lead.source;
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
    await apiClient.patch(`/customers/${detail.value.id}`, editForm);
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
      <el-space>
        <el-button :icon="ArrowLeft" @click="goBack">{{ backTarget.label }}</el-button>
        <el-button :disabled="!detail || !canWriteCustomer" @click="openEditDialog">编辑档案</el-button>
        <el-button type="primary" :disabled="!detail || !canWriteCustomer" @click="openFollowupDialog">
          新增跟进
        </el-button>
        <el-button :disabled="!detail" @click="openLeadDetail">查看线索详情</el-button>
      </el-space>
    </el-card>

    <el-card v-loading="loading" shadow="never">
      <template #header>
        <div class="head">
          <span>客户档案</span>
          <el-tag v-if="detail" type="success" effect="plain">客户ID {{ detail.id }}</el-tag>
        </div>
      </template>

      <el-empty v-if="!detail" description="未找到客户" />
      <template v-else>
        <el-descriptions :column="3" border>
          <el-descriptions-item label="客户名称">{{ detail.name }}</el-descriptions-item>
          <el-descriptions-item label="联系人">{{ detail.contact_name }}</el-descriptions-item>
          <el-descriptions-item label="电话">{{ detail.phone }}</el-descriptions-item>
          <el-descriptions-item label="分配会计">{{ detail.accountant_username }}</el-descriptions-item>
          <el-descriptions-item label="来源模板">{{ templateLabel(detail.lead.template_type) }}</el-descriptions-item>
          <el-descriptions-item label="等级">{{ detail.lead.grade || '-' }}</el-descriptions-item>
          <el-descriptions-item label="微信">{{ detail.lead.contact_wechat || '-' }}</el-descriptions-item>
          <el-descriptions-item label="传真">{{ detail.lead.fax || '-' }}</el-descriptions-item>
          <el-descriptions-item label="其他联系方式">{{ detail.lead.other_contact || '-' }}</el-descriptions-item>
          <el-descriptions-item label="地区">{{ detail.lead.region || '-' }}</el-descriptions-item>
          <el-descriptions-item label="国家/类型">{{ detail.lead.country || '-' }}</el-descriptions-item>
          <el-descriptions-item label="服务开始时间">{{ detail.lead.service_start_text || '-' }}</el-descriptions-item>
          <el-descriptions-item label="企业性质">{{ detail.lead.company_nature || '-' }}</el-descriptions-item>
          <el-descriptions-item label="服务方式">{{ detail.lead.service_mode || '-' }}</el-descriptions-item>
          <el-descriptions-item label="收费标准">{{ detail.lead.fee_standard || '-' }}</el-descriptions-item>
          <el-descriptions-item label="首期账单期间">{{ detail.lead.first_billing_period || '-' }}</el-descriptions-item>
          <el-descriptions-item label="提醒值">{{ detail.lead.reminder_value || '-' }}</el-descriptions-item>
          <el-descriptions-item label="下次提醒">{{ detail.lead.next_reminder_at || '-' }}</el-descriptions-item>
          <el-descriptions-item label="最后跟进日期">{{ detail.lead.last_followup_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="来源">{{ detail.lead.source || '-' }}</el-descriptions-item>
          <el-descriptions-item label="主营/需求" :span="3">{{ detail.lead.main_business || '-' }}</el-descriptions-item>
          <el-descriptions-item label="介绍" :span="3">{{ detail.lead.intro || '-' }}</el-descriptions-item>
          <el-descriptions-item label="备注" :span="3">{{ detail.lead.notes || '-' }}</el-descriptions-item>
        </el-descriptions>
      </template>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="head">
          <span>跟进记录</span>
          <el-tag type="info" effect="plain">{{ detail?.followups.length ?? 0 }} 条</el-tag>
        </div>
      </template>
      <el-table :data="detail?.followups ?? []" stripe border>
        <el-table-column prop="followup_at" label="跟进日期" width="120" />
        <el-table-column prop="feedback" label="跟进反馈" min-width="300" />
        <el-table-column prop="next_reminder_at" label="下次提醒" width="120" />
        <el-table-column prop="notes" label="备注" min-width="220" />
      </el-table>
    </el-card>
  </el-space>

  <el-dialog v-model="showFollowupDialog" title="新增客户跟进" width="520px">
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

  <el-dialog v-model="showEditDialog" title="编辑客户档案" width="900px">
    <el-form label-position="top">
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="客户名称">
            <el-input v-model="editForm.name" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="联系人">
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
        <el-col :span="6">
          <el-form-item label="等级">
            <el-input v-model="editForm.lead_grade" />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="微信">
            <el-input v-model="editForm.lead_contact_wechat" />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="传真">
            <el-input v-model="editForm.lead_fax" />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="提醒值">
            <el-input v-model="editForm.lead_reminder_value" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="地区">
            <el-input v-model="editForm.lead_region" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="国家/类型">
            <el-input v-model="editForm.lead_country" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="来源">
            <el-input v-model="editForm.lead_source" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="服务开始时间">
            <el-input v-model="editForm.lead_service_start_text" />
          </el-form-item>
        </el-col>
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
      </el-row>
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="收费标准">
            <el-input v-model="editForm.lead_fee_standard" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="首期账单期间">
            <el-input v-model="editForm.lead_first_billing_period" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="下次提醒">
            <el-date-picker
              v-model="editForm.lead_next_reminder_at"
              type="date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              :editable="true"
              placeholder="YYYYMMDD 或 YYMMDD"
              @keydown.enter.capture="commitDateInput((v) => (editForm.lead_next_reminder_at = v), $event)"
              @blur.capture="commitDateInput((v) => (editForm.lead_next_reminder_at = v), $event)"
            />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="其他联系方式">
        <el-input v-model="editForm.lead_other_contact" />
      </el-form-item>
      <el-form-item label="主营/需求">
        <el-input v-model="editForm.lead_main_business" type="textarea" :rows="2" />
      </el-form-item>
      <el-form-item label="介绍">
        <el-input v-model="editForm.lead_intro" />
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
}
</style>
