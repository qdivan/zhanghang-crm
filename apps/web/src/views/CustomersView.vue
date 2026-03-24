<script setup lang="ts">
import { MoreFilled } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { apiClient } from "../api/client";
import BillingDraftRowsEditor from "../components/BillingDraftRowsEditor.vue";
import { useResponsive } from "../composables/useResponsive";
import { useAuthStore } from "../stores/auth";
import type { BillingRecord, BillingCreatePayload, CustomerListItem } from "../types";
import {
  createEmptyBillingDraft,
  prepareBillingDraftsForSubmit,
  validateBillingDraft,
} from "../utils/billingDraft";

const router = useRouter();
const auth = useAuthStore();
const { isMobile } = useResponsive();
const loading = ref(false);
const keyword = ref("");
const rows = ref<CustomerListItem[]>([]);
const canManageGrant = computed(() => auth.user?.role === "OWNER" || auth.user?.role === "ADMIN");
const canCreateBilling = computed(
  () => auth.user?.role === "OWNER" || auth.user?.role === "ADMIN" || auth.user?.role === "MANAGER",
);
const showCreateBillingDialog = ref(false);
const creatingBilling = ref(false);
const selectedCustomerForBilling = ref<CustomerListItem | null>(null);
const billingRows = ref<BillingCreatePayload[]>([createEmptyBillingDraft(null)]);

function mobileMetrics(row: CustomerListItem) {
  return [
    { label: "收费标准", value: row.source_fee_standard || "-" },
    { label: "服务项目", value: row.source_main_business || "-" },
    { label: "服务开始", value: row.source_service_start_display || "-" },
    { label: "会计", value: row.accountant_username || "-" },
    { label: "最后跟进", value: row.source_last_followup_date || "-" },
  ].filter((item) => item.value !== "-");
}

async function fetchCustomers() {
  loading.value = true;
  try {
    const resp = await apiClient.get<CustomerListItem[]>("/customers", {
      params: {
        keyword: keyword.value || undefined,
      },
    });
    rows.value = resp.data;
  } catch (error) {
    ElMessage.error("获取客户列表失败");
  } finally {
    loading.value = false;
  }
}

function openCustomerDetail(row: CustomerListItem) {
  router.push(`/customers/${row.id}`);
}

function openLeadDetail(row: CustomerListItem) {
  router.push({
    path: `/leads/${row.source_lead_id}`,
    query: { from: "customers" },
  });
}

function openGrantSettings() {
  router.push({
    path: "/admin/users",
    query: { tab: "grants" },
  });
}

function resetBillingRows(customerId: number | null = null) {
  billingRows.value = [createEmptyBillingDraft(customerId)];
}

function openCreateBillingDialog(row: CustomerListItem) {
  if (!canCreateBilling.value) return;
  resetBillingRows(row.id);
  selectedCustomerForBilling.value = row;
  showCreateBillingDialog.value = true;
}

function handleMobileCommand(command: string, row: CustomerListItem) {
  if (command === "detail") openCustomerDetail(row);
  if (command === "billing") openCreateBillingDialog(row);
  if (command === "lead") openLeadDetail(row);
}

function onMobileMenuCommand(command: { action: string; row: CustomerListItem }) {
  handleMobileCommand(command.action, command.row);
}

function handleCreateBillingDialogClosed() {
  resetBillingRows();
  selectedCustomerForBilling.value = null;
}

async function createBillingRecordForCustomer() {
  const validationError = billingRows.value
    .map((item, index) => validateBillingDraft(item, index))
    .find((item) => item);
  if (validationError) {
    ElMessage.warning(validationError);
    return;
  }
  creatingBilling.value = true;
  try {
    const payload = prepareBillingDraftsForSubmit(billingRows.value);
    const resp = await apiClient.post<BillingRecord[]>("/billing-records/batch", { records: payload });
    showCreateBillingDialog.value = false;
    ElMessage.success(`已创建 ${resp.data.length} 条收费记录`);
    resetBillingRows();
    selectedCustomerForBilling.value = null;
  } catch (error) {
    ElMessage.error("创建收费记录失败");
  } finally {
    creatingBilling.value = false;
  }
}

onMounted(fetchCustomers);
</script>

<template>
  <el-space direction="vertical" fill :size="12">
    <el-card shadow="never">
      <el-form inline @submit.prevent="fetchCustomers" class="customers-filter-form">
        <el-form-item label="关键词">
          <el-input
            v-model="keyword"
            placeholder="客户/联系人/电话/会计"
            clearable
            @keyup.enter="fetchCustomers"
          />
        </el-form-item>
        <el-form-item>
          <el-button @click="fetchCustomers">查询</el-button>
          <el-button v-if="canManageGrant" type="primary" plain @click="openGrantSettings">数据授权配置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="head">
          <div>
            <div class="card-title">客户列表</div>
            <div class="card-subtitle">这里只显示已成交客户，转给会计或经办人后在这里继续维护。</div>
          </div>
          <el-tag type="success" effect="plain">{{ rows.length }} 条</el-tag>
        </div>
      </template>
      <div v-if="isMobile" v-loading="loading" class="mobile-record-list">
        <div v-for="row in rows" :key="row.id" class="mobile-record-card">
          <div class="mobile-record-head">
            <div class="mobile-record-main">
              <el-button link type="primary" class="mobile-record-title" @click="openCustomerDetail(row)">
                {{ row.name }}
              </el-button>
              <div class="mobile-record-subtitle">
                {{ row.contact_name || "-" }} / {{ row.phone || "-" }}
              </div>
            </div>
            <el-tag size="small" effect="plain">{{ row.accountant_username || "-" }}</el-tag>
          </div>

          <div class="mobile-record-metrics">
            <div v-for="item in mobileMetrics(row)" :key="`${row.id}-${item.label}`" class="mobile-metric">
              <div class="mobile-metric-label">{{ item.label }}</div>
              <div class="mobile-metric-value">{{ item.value }}</div>
            </div>
          </div>

          <div v-if="row.source_main_business || row.source_intro" class="mobile-record-note">
            <div v-if="row.source_main_business">主营：{{ row.source_main_business }}</div>
            <div v-if="row.source_intro">介绍人：{{ row.source_intro }}</div>
          </div>

          <div class="mobile-actions">
            <el-button size="small" type="primary" @click="openCustomerDetail(row)">客户档案</el-button>
            <el-button v-if="canCreateBilling" size="small" type="success" plain @click="openCreateBillingDialog(row)">
              新增收费
            </el-button>
            <el-dropdown trigger="click" @command="onMobileMenuCommand">
              <el-button size="small" plain>
                更多
                <el-icon><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item :command="{ action: 'lead', row }">开发来源</el-dropdown-item>
                  <el-dropdown-item v-if="canCreateBilling" :command="{ action: 'billing', row }">新增收费</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>
      <el-table v-else v-loading="loading" :data="rows" stripe border>
        <el-table-column prop="id" label="序号" width="80" />
        <el-table-column label="客户号+公司名" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <el-button link type="primary" @click="openCustomerDetail(row)">{{ row.name }}</el-button>
          </template>
        </el-table-column>
        <el-table-column
          prop="source_fee_standard"
          label="收费标准"
          min-width="130"
          show-overflow-tooltip
        />
        <el-table-column
          prop="source_main_business"
          label="服务项目/主营"
          min-width="180"
          show-overflow-tooltip
        />
        <el-table-column
          prop="source_grade"
          label="等级"
          width="110"
          show-overflow-tooltip
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="source_service_start_display"
          label="服务开始"
          width="110"
        />
        <el-table-column
          prop="contact_name"
          label="对接人及电话"
          min-width="160"
        >
          <template #default="{ row }">{{ `${row.contact_name || "-"} / ${row.phone || "-"}` }}</template>
        </el-table-column>
        <el-table-column
          prop="source_last_followup_date"
          label="最后跟进"
          width="110"
        />
        <el-table-column
          prop="accountant_username"
          label="会计"
          width="110"
        />
        <el-table-column
          label="操作"
          width="200"
        >
          <template #default="{ row }">
            <el-space class="table-action-wrap">
              <el-button link type="primary" @click="openCustomerDetail(row)">客户档案</el-button>
              <el-button v-if="canCreateBilling" link type="success" @click="openCreateBillingDialog(row)">
                新增收费
              </el-button>
              <el-button link @click="openLeadDetail(row)">开发来源</el-button>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </el-space>

  <el-dialog
    v-model="showCreateBillingDialog"
    title="新增收费记录"
    width="760px"
    @closed="handleCreateBillingDialogClosed"
  >
    <el-form label-position="top">
      <el-form-item label="客户">
        <el-input
          :model-value="selectedCustomerForBilling ? `${selectedCustomerForBilling.name}（${selectedCustomerForBilling.contact_name}）` : ''"
          disabled
        />
      </el-form-item>
      <el-text type="info" size="small">
        同一客户可以连续增行多个收费项目，统一保存。常规新单只需填写收费类别、金额、服务开始日期、到期日期。
      </el-text>
    </el-form>
    <BillingDraftRowsEditor v-model="billingRows" title-prefix="收费明细" />
    <template #footer>
      <el-button @click="showCreateBillingDialog = false">取消</el-button>
      <el-button type="primary" :loading="creatingBilling" @click="createBillingRecordForCustomer">
        保存 {{ billingRows.length }} 条
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.card-title {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}

.card-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
}

@media (max-width: 900px) {
  .customers-filter-form {
    display: flex;
    flex-wrap: wrap;
  }

  .mobile-actions :deep(.el-button) {
    margin-left: 0;
  }
}
</style>
