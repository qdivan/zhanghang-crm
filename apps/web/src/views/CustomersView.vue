<script setup lang="ts">
import { QuestionFilled } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";

import { apiClient } from "../api/client";
import { useAuthStore } from "../stores/auth";
import { commitDateInput } from "../utils/dateInput";
import type { CustomerListItem } from "../types";

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

const router = useRouter();
const auth = useAuthStore();
const loading = ref(false);
const keyword = ref("");
const rows = ref<CustomerListItem[]>([]);
const canManageGrant = computed(() => auth.user?.role === "OWNER" || auth.user?.role === "ADMIN");
const canCreateBilling = computed(() => auth.user?.role === "OWNER" || auth.user?.role === "ADMIN");
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
const showCreateBillingDialog = ref(false);
const creatingBilling = ref(false);
const selectedCustomerForBilling = ref<CustomerListItem | null>(null);
const billingForm = reactive<BillingCreateForm>({
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
const billingCycleOptions = [
  "按月（每月收）",
  "按季（每3个月收）",
  "半年（每6个月收）",
  "全年（每12个月收）",
  "一次性（单次服务）",
  "自定义周期（见备注）",
];

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

function applyBillingModeDefaults() {
  if (billingForm.charge_mode === "ONE_TIME") {
    billingForm.amount_basis = "ONE_TIME";
    billingForm.period_start_month = "";
    billingForm.period_end_month = "";
    if (!billingForm.due_month) {
      billingForm.due_month = new Date().toISOString().slice(0, 10);
    }
  } else {
    if (billingForm.amount_basis === "ONE_TIME") {
      billingForm.amount_basis = "MONTHLY";
    }
    if (billingForm.period_start_month && !billingForm.period_end_month) {
      billingForm.period_end_month = shiftMonth(billingForm.period_start_month, 11);
    }
  }
}

function onBillingModeChange() {
  applyBillingModeDefaults();
}

function onPeriodStartMonthChange() {
  if (billingForm.charge_mode === "PERIODIC" && billingForm.period_start_month) {
    billingForm.period_end_month = shiftMonth(billingForm.period_start_month, 11);
    billingForm.collection_start_date = `${billingForm.period_start_month}-01`;
  }
}

function templateLabel(template: string) {
  if (template === "FOLLOWUP") return "客户跟进";
  if (template === "REDEVELOP") return "老客二开";
  return "转化";
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

function resetBillingForm() {
  billingForm.serial_no = null;
  billingForm.customer_id = null;
  billingForm.charge_category = "代账";
  billingForm.charge_mode = "PERIODIC";
  billingForm.amount_basis = "MONTHLY";
  billingForm.summary = "";
  billingForm.total_fee = 0;
  billingForm.monthly_fee = 0;
  billingForm.billing_cycle_text = "按月（每月收）";
  billingForm.period_start_month = "";
  billingForm.period_end_month = "";
  billingForm.collection_start_date = "";
  billingForm.due_month = "";
  billingForm.payment_method = "预收";
  billingForm.status = "PARTIAL";
  billingForm.received_amount = 0;
  billingForm.note = "";
  billingForm.extra_note = "";
  billingForm.color_tag = "";
  applyBillingModeDefaults();
}

function syncBillingDerivedDates() {
  applyBillingModeDefaults();
  if (billingForm.charge_mode === "PERIODIC") {
    if (billingForm.period_start_month && !billingForm.collection_start_date) {
      billingForm.collection_start_date = `${billingForm.period_start_month}-01`;
    }
    if (billingForm.period_end_month && !billingForm.due_month) {
      billingForm.due_month = `${billingForm.period_end_month}-28`;
    }
  } else if (!billingForm.collection_start_date) {
    billingForm.collection_start_date = billingForm.due_month || new Date().toISOString().slice(0, 10);
  }
}

function openCreateBillingDialog(row: CustomerListItem) {
  if (!canCreateBilling.value) return;
  resetBillingForm();
  selectedCustomerForBilling.value = row;
  billingForm.customer_id = row.id;
  showCreateBillingDialog.value = true;
}

function handleCreateBillingDialogClosed() {
  resetBillingForm();
  selectedCustomerForBilling.value = null;
}

async function createBillingRecordForCustomer() {
  if (!billingForm.customer_id) {
    ElMessage.warning("客户信息缺失，无法创建收费记录");
    return;
  }
  syncBillingDerivedDates();
  creatingBilling.value = true;
  try {
    await apiClient.post("/billing-records", billingForm);
    showCreateBillingDialog.value = false;
    ElMessage.success("收费记录已创建");
    resetBillingForm();
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
          <span>客户列表（已转化）</span>
          <el-tag type="success" effect="plain">{{ rows.length }} 条</el-tag>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe border>
        <el-table-column prop="id" label="客户ID" width="90" />
        <el-table-column label="客户名称" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <el-button link type="primary" @click="openCustomerDetail(row)">{{ row.name }}</el-button>
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
          prop="accountant_username"
          label="会计"
          width="110"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          label="来源模板"
          width="95"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        >
          <template #default="{ row }">{{ templateLabel(row.source_template_type) }}</template>
        </el-table-column>
        <el-table-column
          prop="source_grade"
          label="等级"
          width="70"
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
          label="操作"
          width="220"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        >
          <template #default="{ row }">
            <el-space class="table-action-wrap">
              <el-button link type="primary" @click="openCustomerDetail(row)">客户档案</el-button>
              <el-button link @click="openLeadDetail(row)">线索详情</el-button>
              <el-button v-if="canCreateBilling" link type="success" @click="openCreateBillingDialog(row)">
                新增收费
              </el-button>
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
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="序号">
            <el-input-number
              v-model="billingForm.serial_no"
              :min="1"
              :controls="false"
              style="width:100%"
              placeholder="留空自动编号"
            />
          </el-form-item>
        </el-col>
        <el-col :span="16">
          <el-form-item label="客户">
            <el-input :model-value="selectedCustomerForBilling ? `${selectedCustomerForBilling.name}（${selectedCustomerForBilling.contact_name}）` : ''" disabled />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="12">
        <el-col :span="6">
          <el-form-item label="收费类别">
            <el-select v-model="billingForm.charge_category">
              <el-option
                v-for="item in chargeCategoryOptions"
                :key="`customer-category-${item}`"
                :label="item"
                :value="item"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="计费方式">
            <el-select v-model="billingForm.charge_mode" @change="onBillingModeChange">
              <el-option
                v-for="item in chargeModeOptions"
                :key="`customer-mode-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="金额口径">
            <el-select v-model="billingForm.amount_basis">
              <el-option
                v-for="item in amountBasisOptions"
                :key="`customer-basis-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="摘要">
            <el-input v-model="billingForm.summary" placeholder="例如：股权变更服务费" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="6"><el-form-item label="总费用"><el-input-number v-model="billingForm.total_fee" :min="0" :controls="false" style="width:100%" /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="月费用"><el-input-number v-model="billingForm.monthly_fee" :min="0" :controls="false" style="width:100%" /></el-form-item></el-col>
        <el-col :span="6">
          <el-form-item label="开始月份">
            <el-date-picker
              v-model="billingForm.period_start_month"
              type="month"
              format="YYYY-MM"
              value-format="YYYY-MM"
              :disabled="billingForm.charge_mode === 'ONE_TIME'"
              placeholder="YYYY-MM"
              @change="onPeriodStartMonthChange"
            />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="结束月份">
            <el-date-picker
              v-model="billingForm.period_end_month"
              type="month"
              format="YYYY-MM"
              value-format="YYYY-MM"
              :disabled="billingForm.charge_mode === 'ONE_TIME'"
              placeholder="YYYY-MM"
            />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="6">
          <el-form-item label="起收日期（精确）">
            <el-date-picker
              v-model="billingForm.collection_start_date"
              type="date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              :editable="true"
              placeholder="YYYYMMDD 或 YYMMDD"
              @keydown.enter.capture="commitDateInput((v) => (billingForm.collection_start_date = v), $event)"
              @blur.capture="commitDateInput((v) => (billingForm.collection_start_date = v), $event)"
            />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="到期日">
            <el-date-picker
              v-model="billingForm.due_month"
              type="date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              :editable="true"
              placeholder="YYYYMMDD 或 YYMMDD"
              @keydown.enter.capture="commitDateInput((v) => (billingForm.due_month = v), $event)"
              @blur.capture="commitDateInput((v) => (billingForm.due_month = v), $event)"
            />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-text type="info" size="small">
            {{ billingForm.charge_mode === "ONE_TIME" ? "按次：默认当天到期" : "按期：默认结束月份=开始月份+11" }}
          </el-text>
        </el-col>
      </el-row>

      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item>
            <template #label>
              <span class="label-with-help">
                付款方式
                <el-tooltip placement="top" :show-after="150">
                  <template #content>
                    <div>预收：服务开始前先收费</div>
                    <div>后收：到期日/账期结束后再收费</div>
                  </template>
                  <el-icon class="help-icon"><QuestionFilled /></el-icon>
                </el-tooltip>
              </span>
            </template>
            <el-select v-model="billingForm.payment_method">
              <el-option
                v-for="item in paymentMethodOptions"
                :key="`customer-create-method-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item>
            <template #label>
              <span class="label-with-help">
                台账状态
                <el-tooltip placement="top" :show-after="150">
                  <template #content>
                    <div>清账：已收齐，未收金额为 0</div>
                    <div>部分收费：已收部分，仍有未收</div>
                    <div>全欠：尚未收款</div>
                  </template>
                  <el-icon class="help-icon"><QuestionFilled /></el-icon>
                </el-tooltip>
              </span>
            </template>
            <el-select v-model="billingForm.status">
              <el-option
                v-for="item in billingStatusOptions"
                :key="`customer-create-status-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8"><el-form-item label="已收金额"><el-input-number v-model="billingForm.received_amount" :min="0" :controls="false" style="width:100%" /></el-form-item></el-col>
      </el-row>

      <el-form-item label="代账周期">
        <el-select v-model="billingForm.billing_cycle_text" placeholder="请选择代账周期">
          <el-option
            v-for="item in billingCycleOptions"
            :key="`customer-cycle-${item}`"
            :label="item"
            :value="item"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="billingForm.note" type="textarea" :rows="2" />
      </el-form-item>
      <el-form-item label="扩展说明">
        <el-input v-model="billingForm.extra_note" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showCreateBillingDialog = false">取消</el-button>
      <el-button type="primary" :loading="creatingBilling" @click="createBillingRecordForCustomer">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.label-with-help {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.help-icon {
  color: #909399;
  font-size: 14px;
  cursor: help;
}

@media (max-width: 900px) {
  .customers-filter-form {
    display: flex;
    flex-wrap: wrap;
  }
}
</style>
