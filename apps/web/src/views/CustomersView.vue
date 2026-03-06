<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { apiClient } from "../api/client";
import BillingDraftRowsEditor from "../components/BillingDraftRowsEditor.vue";
import { useAuthStore } from "../stores/auth";
import type { BillingRecord, BillingCreatePayload, CustomerListItem } from "../types";
import {
  createEmptyBillingDraft,
  prepareBillingDraftsForSubmit,
  validateBillingDraft,
} from "../utils/billingDraft";

const router = useRouter();
const auth = useAuthStore();
const loading = ref(false);
const keyword = ref("");
const rows = ref<CustomerListItem[]>([]);
const canManageGrant = computed(() => auth.user?.role === "OWNER" || auth.user?.role === "ADMIN");
const canCreateBilling = computed(() => auth.user?.role === "OWNER" || auth.user?.role === "ADMIN");
const showCreateBillingDialog = ref(false);
const creatingBilling = ref(false);
const selectedCustomerForBilling = ref<CustomerListItem | null>(null);
const billingRows = ref<BillingCreatePayload[]>([createEmptyBillingDraft(null)]);

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
          <span>客户列表（对齐 `客户跟进表 > 客户总览`）</span>
          <el-tag type="success" effect="plain">{{ rows.length }} 条</el-tag>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe border>
        <el-table-column prop="id" label="序号" width="80" />
        <el-table-column label="客户号+公司名" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <el-button link type="primary" @click="openCustomerDetail(row)">{{ row.name }}</el-button>
          </template>
        </el-table-column>
        <el-table-column
          prop="source_grade"
          label="等级"
          width="70"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="source_area_display"
          label="国家/类型"
          width="110"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="source_service_start_display"
          label="服务开始"
          width="110"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="source_company_nature"
          label="企业性质"
          width="100"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="source_service_mode"
          label="服务方式"
          width="100"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="contact_name"
          label="对接人及电话"
          min-width="160"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        >
          <template #default="{ row }">{{ `${row.contact_name || "-"} / ${row.phone || "-"}` }}</template>
        </el-table-column>
        <el-table-column
          prop="source_contact_wechat"
          label="微信"
          width="120"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="source_other_contact"
          label="其他联系人"
          min-width="140"
          show-overflow-tooltip
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="source_main_business"
          label="主营产品"
          min-width="160"
          show-overflow-tooltip
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="source_intro"
          label="介绍"
          min-width="140"
          show-overflow-tooltip
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="source_fee_standard"
          label="收费标准"
          min-width="120"
          show-overflow-tooltip
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="source_first_billing_period"
          label="首期账单期间"
          width="120"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="source_last_followup_date"
          label="最后跟进"
          width="110"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="source_reminder_value"
          label="提醒值"
          width="90"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="accountant_username"
          label="会计"
          width="110"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          label="操作"
          width="200"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
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
}

@media (max-width: 900px) {
  .customers-filter-form {
    display: flex;
    flex-wrap: wrap;
  }
}
</style>
