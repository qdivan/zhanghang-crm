<script setup lang="ts">
import { ArrowLeft } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { apiClient } from "../api/client";
import FlexibleDateInput from "../components/shared/FlexibleDateInput.vue";
import { useResponsive } from "../composables/useResponsive";
import { useAuthStore } from "../stores/auth";
import type { CustomerDetail } from "../types";
import { todayInBrowserTimeZone } from "../utils/time";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const { isMobile } = useResponsive();
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

const displayCountry = computed(() => detail.value?.lead.country || detail.value?.lead.region || "-");
const displayServiceStart = computed(
  () => detail.value?.lead.service_start_text || detail.value?.lead.contact_start_date || "-",
);
const displayContactLine = computed(() => {
  if (!detail.value) return "-";
  return [detail.value.contact_name, detail.value.phone].filter(Boolean).join(" / ") || "-";
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
        <el-button type="primary" :disabled="!detail || !canWriteCustomer" @click="openFollowupDialog">
          新增跟进
        </el-button>
        <el-button :disabled="!detail" @click="openLeadDetail">查看开发来源</el-button>
      </el-space>
    </el-card>

    <el-card v-loading="loading" shadow="never">
      <template #header>
        <div class="head">
          <span>{{ isMobile ? "客户档案" : "客户档案（对齐 `客户跟进表` 明细页）" }}</span>
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
                <div class="detail-long-label">介绍</div>
                <div class="detail-long-value">{{ detail.lead.intro || "-" }}</div>
              </div>
              <div class="detail-long-field">
                <div class="detail-long-label">备注</div>
                <div class="detail-long-value">{{ detail.lead.notes || "-" }}</div>
              </div>
            </div>
          </div>
        </div>
        <el-descriptions v-else :column="2" border>
          <el-descriptions-item label="公司名">{{ detail.name }}</el-descriptions-item>
          <el-descriptions-item label="等级">{{ detail.lead.grade || '-' }}</el-descriptions-item>
          <el-descriptions-item label="国家">{{ displayCountry }}</el-descriptions-item>
          <el-descriptions-item label="服务开始时间">{{ displayServiceStart }}</el-descriptions-item>
          <el-descriptions-item label="企业性质">{{ detail.lead.company_nature || '-' }}</el-descriptions-item>
          <el-descriptions-item label="服务方式">{{ detail.lead.service_mode || '-' }}</el-descriptions-item>
          <el-descriptions-item label="对接人及电话">{{ displayContactLine }}</el-descriptions-item>
          <el-descriptions-item label="微信">{{ detail.lead.contact_wechat || '-' }}</el-descriptions-item>
          <el-descriptions-item label="其他联系人">{{ detail.lead.other_contact || '-' }}</el-descriptions-item>
          <el-descriptions-item label="收费标准">{{ detail.lead.fee_standard || '-' }}</el-descriptions-item>
          <el-descriptions-item label="首期账单期间">{{ detail.lead.first_billing_period || '-' }}</el-descriptions-item>
          <el-descriptions-item label="最后跟进日期">{{ detail.lead.last_followup_date || '-' }}</el-descriptions-item>
          <el-descriptions-item label="提醒值">{{ detail.lead.reminder_value || '-' }}</el-descriptions-item>
          <el-descriptions-item label="下次提醒">{{ detail.lead.next_reminder_at || '-' }}</el-descriptions-item>
          <el-descriptions-item label="主营产品" :span="2">{{ detail.lead.main_business || '-' }}</el-descriptions-item>
          <el-descriptions-item label="介绍" :span="2">{{ detail.lead.intro || '-' }}</el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">{{ detail.lead.notes || '-' }}</el-descriptions-item>
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
      <div v-if="isMobile" class="mobile-record-list">
        <div v-for="item in detail?.followups ?? []" :key="item.id" class="mobile-record-card">
          <div class="mobile-record-head">
            <div class="mobile-record-main">
              <div class="mobile-record-title">{{ item.followup_at }}</div>
              <div class="mobile-record-subtitle">下次提醒：{{ item.next_reminder_at || "-" }}</div>
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
      <el-table v-else :data="detail?.followups ?? []" stripe border>
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
            <FlexibleDateInput v-model="followupForm.followup_at" :empty-value="''" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
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
            <el-input v-model="editForm.lead_grade" />
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
            <el-input v-model="editForm.lead_reminder_value" />
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
      <el-form-item label="介绍">
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
