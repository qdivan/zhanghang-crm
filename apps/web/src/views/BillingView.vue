<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";

import { apiClient } from "../api/client";
import type { BillingActivity, BillingRecord, CustomerListItem } from "../types";
import { commitDateInput } from "../utils/dateInput";
import { todayInBrowserTimeZone } from "../utils/time";

type BillingCreateForm = {
  serial_no: number | null;
  customer_id: number | null;
  total_fee: number;
  monthly_fee: number;
  billing_cycle_text: string;
  due_month: string;
  payment_method: string;
  status: "CLEARED" | "FULL_ARREARS" | "PARTIAL";
  received_amount: number;
  note: string;
  extra_note: string;
  color_tag: string;
};

type ActivityForm = {
  activity_type: "REMINDER" | "PAYMENT";
  occurred_at: string;
  amount: number;
  payment_nature: "" | "MONTHLY" | "YEARLY" | "ONE_OFF";
  is_prepay: boolean;
  is_settlement: boolean;
  content: string;
  next_followup_at: string | null;
  note: string;
};

const router = useRouter();
const loading = ref(false);
const rows = ref<BillingRecord[]>([]);
const customers = ref<CustomerListItem[]>([]);
const summary = ref({
  total_records: 0,
  total_fee: 0,
  total_monthly_fee: 0,
  payment_method_distribution: [] as Array<{ payment_method: string; count: number }>,
  status_distribution: [] as Array<{ status: string; count: number }>,
});

const filters = reactive({
  keyword: "",
  payment_method: "",
  status: "",
});

const showCreateDialog = ref(false);
const createForm = reactive<BillingCreateForm>({
  serial_no: null,
  customer_id: null,
  total_fee: 0,
  monthly_fee: 0,
  billing_cycle_text: "",
  due_month: "",
  payment_method: "预收",
  status: "PARTIAL",
  received_amount: 0,
  note: "",
  extra_note: "",
  color_tag: "",
});

const showActivityDrawer = ref(false);
const activityLoading = ref(false);
const activityRows = ref<BillingActivity[]>([]);
const selectedRecord = ref<BillingRecord | null>(null);
const activityForm = reactive<ActivityForm>({
  activity_type: "REMINDER",
  occurred_at: todayInBrowserTimeZone(),
  amount: 0,
  payment_nature: "",
  is_prepay: false,
  is_settlement: false,
  content: "",
  next_followup_at: null,
  note: "",
});

function readActivityTypeToken(value: unknown): string {
  if (typeof value === "string") {
    return value.trim();
  }
  if (value && typeof value === "object") {
    const maybeValue = (value as Record<string, unknown>).value;
    if (typeof maybeValue === "string") {
      return maybeValue.trim();
    }
    const maybeLabel = (value as Record<string, unknown>).label;
    if (typeof maybeLabel === "string") {
      return maybeLabel.trim();
    }
    const maybeType = (value as Record<string, unknown>).activity_type;
    if (typeof maybeType === "string") {
      return maybeType.trim();
    }
  }
  return "";
}

function normalizeActivityType(value: unknown): "REMINDER" | "PAYMENT" {
  const token = readActivityTypeToken(value);
  const upper = token.toUpperCase();
  if (upper === "PAYMENT" || token.includes("收款")) {
    return "PAYMENT";
  }
  return "REMINDER";
}

function isPaymentActivityType(value: unknown): boolean {
  const token = readActivityTypeToken(value);
  const upper = token.toUpperCase();
  if (!token) return false;
  if (upper === "REMINDER" || token.includes("催收")) return false;
  if (upper === "PAYMENT" || token.includes("收款")) return true;
  // 未识别值时优先放开输入，避免“已选收款但金额无法填写”的阻塞
  return true;
}

const isPaymentActivity = computed(() => isPaymentActivityType(activityForm.activity_type));

function statusLabel(status: string) {
  if (status === "CLEARED") return "清账";
  if (status === "FULL_ARREARS") return "全欠";
  return "部分收费";
}

function statusTagType(status: string) {
  if (status === "CLEARED") return "success";
  if (status === "FULL_ARREARS") return "danger";
  return "warning";
}

function activityTypeLabel(type: string) {
  return type === "PAYMENT" ? "收款" : "催收";
}

async function fetchRecords() {
  loading.value = true;
  try {
    const resp = await apiClient.get<BillingRecord[]>("/billing-records", {
      params: {
        keyword: filters.keyword || undefined,
        payment_method: filters.payment_method || undefined,
      },
    });
    rows.value = filters.status ? resp.data.filter((item) => item.status === filters.status) : resp.data;
  } catch (error) {
    ElMessage.error("获取收费记录失败");
  } finally {
    loading.value = false;
  }
}

async function fetchSummary() {
  try {
    const resp = await apiClient.get("/billing-records/summary");
    summary.value = resp.data;
  } catch (error) {
    ElMessage.error("获取收费统计失败");
  }
}

async function fetchCustomers() {
  try {
    const resp = await apiClient.get<CustomerListItem[]>("/customers");
    customers.value = resp.data;
  } catch (error) {
    ElMessage.error("获取客户列表失败");
  }
}

async function createRecord() {
  if (!createForm.customer_id) {
    ElMessage.warning("请先选择客户");
    return;
  }
  try {
    await apiClient.post("/billing-records", createForm);
    ElMessage.success("收费记录已创建");
    showCreateDialog.value = false;
    resetCreateForm();
    await fetchRecords();
    await fetchSummary();
  } catch (error) {
    ElMessage.error("创建失败（需老板/管理员账号）");
  }
}

function resetCreateForm() {
  createForm.serial_no = null;
  createForm.customer_id = null;
  createForm.total_fee = 0;
  createForm.monthly_fee = 0;
  createForm.billing_cycle_text = "";
  createForm.due_month = "";
  createForm.payment_method = "预收";
  createForm.status = "PARTIAL";
  createForm.received_amount = 0;
  createForm.note = "";
  createForm.extra_note = "";
  createForm.color_tag = "";
}

function openCreateDialog() {
  resetCreateForm();
  showCreateDialog.value = true;
}

function openCustomerDetail(record: BillingRecord) {
  if (!record.customer_id) {
    ElMessage.warning("该收费记录未关联客户档案，请先在收费记录里选择客户");
    return;
  }
  router.push(`/customers/${record.customer_id}`);
}

function resetActivityForm() {
  activityForm.activity_type = "REMINDER";
  activityForm.occurred_at = todayInBrowserTimeZone();
  activityForm.amount = 0;
  activityForm.payment_nature = "";
  activityForm.is_prepay = false;
  activityForm.is_settlement = false;
  activityForm.content = "";
  activityForm.next_followup_at = null;
  activityForm.note = "";
}

function onActivityTypeChange(value: unknown) {
  const paymentMode = isPaymentActivityType(value);
  activityForm.activity_type = paymentMode ? "PAYMENT" : "REMINDER";
  if (!paymentMode) {
    activityForm.amount = 0;
    activityForm.payment_nature = "";
    activityForm.is_prepay = false;
    activityForm.is_settlement = false;
  }
}

async function fetchActivities() {
  if (!selectedRecord.value) return;
  activityLoading.value = true;
  try {
    const resp = await apiClient.get<BillingActivity[]>(
      `/billing-records/${selectedRecord.value.id}/activities`,
    );
    activityRows.value = resp.data;
  } catch (error) {
    ElMessage.error("获取催收/收款记录失败");
    activityRows.value = [];
  } finally {
    activityLoading.value = false;
  }
}

async function openActivityDrawer(record: BillingRecord) {
  selectedRecord.value = record;
  showActivityDrawer.value = true;
  resetActivityForm();
  await fetchActivities();
}

async function submitActivity() {
  if (!selectedRecord.value) return;
  const normalizedType = normalizeActivityType(activityForm.activity_type);
  const paymentMode = normalizedType === "PAYMENT";
  activityForm.activity_type = normalizedType;
  if (!activityForm.content.trim()) {
    ElMessage.warning("请填写沟通内容");
    return;
  }
  if (paymentMode && activityForm.amount <= 0) {
    ElMessage.warning("收款金额必须大于 0");
    return;
  }
  const payload =
    paymentMode
      ? { ...activityForm, activity_type: "PAYMENT" as const }
      : {
          ...activityForm,
          activity_type: "REMINDER" as const,
          amount: 0,
          payment_nature: "",
          is_prepay: false,
          is_settlement: false,
        };
  try {
    await apiClient.post(`/billing-records/${selectedRecord.value.id}/activities`, payload);
    ElMessage.success("记录已保存");
    resetActivityForm();
    await fetchActivities();
    await fetchRecords();
    await fetchSummary();
  } catch (error) {
    ElMessage.error("保存失败");
  }
}

onMounted(async () => {
  await fetchRecords();
  await fetchSummary();
  await fetchCustomers();
});
</script>

<template>
  <el-space direction="vertical" fill :size="12">
    <el-row :gutter="12">
      <el-col :xs="24" :md="8">
        <el-card shadow="never">
          <el-statistic title="记录数" :value="summary.total_records" />
        </el-card>
      </el-col>
      <el-col :xs="24" :md="8">
        <el-card shadow="never">
          <el-statistic title="总费用" :value="summary.total_fee" />
        </el-card>
      </el-col>
      <el-col :xs="24" :md="8">
        <el-card shadow="never">
          <el-statistic title="月费用合计" :value="summary.total_monthly_fee" />
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <el-form inline @submit.prevent="fetchRecords" class="billing-filter-form">
        <el-form-item label="关键词">
          <el-input
            v-model="filters.keyword"
            placeholder="序号/客户/备注"
            clearable
            @keyup.enter="fetchRecords"
          />
        </el-form-item>
        <el-form-item label="付款方式">
          <el-select v-model="filters.payment_method" placeholder="全部" clearable>
            <el-option label="预收" value="预收" />
            <el-option label="年底收" value="年底收" />
            <el-option label="半年付费" value="半年付费" />
            <el-option label="半年收" value="半年收" />
            <el-option label="后收" value="后收" />
            <el-option label="核定不收费" value="核定不收费" />
          </el-select>
        </el-form-item>
        <el-form-item label="台账状态">
          <el-select v-model="filters.status" placeholder="全部" clearable>
            <el-option label="清账" value="CLEARED" />
            <el-option label="全欠" value="FULL_ARREARS" />
            <el-option label="部分收费" value="PARTIAL" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button @click="fetchRecords">查询</el-button>
          <el-button type="primary" @click="openCreateDialog">新增收费记录</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="head">
          <span>收费台账（对齐 `周 (2)` 结构）</span>
          <el-tag type="success" effect="plain">{{ rows.length }} 条</el-tag>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe border>
        <el-table-column
          prop="serial_no"
          label="序号"
          width="90"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column label="名称" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <el-button link type="primary" @click="openCustomerDetail(row)">
              {{ row.customer_name }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column
          prop="accountant_username"
          label="会计"
          width="100"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="total_fee"
          label="总费用"
          width="90"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="received_amount"
          label="已收"
          width="85"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column prop="outstanding_amount" label="未收" width="80" />
        <el-table-column
          label="状态"
          width="90"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        >
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="monthly_fee"
          label="月费用"
          width="85"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="billing_cycle_text"
          label="代账周期"
          min-width="170"
          show-overflow-tooltip
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="due_month"
          label="到期日"
          width="100"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="payment_method"
          label="付款方式"
          width="90"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="note"
          label="备注"
          min-width="160"
          show-overflow-tooltip
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="extra_note"
          label="扩展"
          min-width="120"
          show-overflow-tooltip
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column label="操作" width="88">
          <template #default="{ row }">
            <el-button link type="primary" @click="openActivityDrawer(row)">催收/收款</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-row :gutter="12">
      <el-col :xs="24" :md="12">
        <el-card shadow="never">
          <template #header>付款方式分布</template>
          <el-space wrap>
            <el-tag
              v-for="item in summary.payment_method_distribution"
              :key="item.payment_method"
              type="info"
              effect="plain"
            >
              {{ item.payment_method }}：{{ item.count }}
            </el-tag>
          </el-space>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card shadow="never">
          <template #header>状态分布</template>
          <el-space wrap>
            <el-tag
              v-for="item in summary.status_distribution"
              :key="item.status"
              :type="statusTagType(item.status)"
              effect="plain"
            >
              {{ statusLabel(item.status) }}：{{ item.count }}
            </el-tag>
          </el-space>
        </el-card>
      </el-col>
    </el-row>
  </el-space>

  <el-dialog v-model="showCreateDialog" title="新增收费记录" width="760px">
    <el-form label-position="top">
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="序号">
            <el-input-number
              v-model="createForm.serial_no"
              :min="1"
              :controls="false"
              style="width:100%"
              placeholder="留空自动编号"
            />
          </el-form-item>
        </el-col>
        <el-col :span="16">
          <el-form-item label="客户">
            <el-select v-model="createForm.customer_id" filterable placeholder="请选择客户">
              <el-option
                v-for="item in customers"
                :key="item.id"
                :label="`${item.name}（${item.contact_name}）`"
                :value="item.id"
              />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="6"><el-form-item label="总费用"><el-input-number v-model="createForm.total_fee" :min="0" :controls="false" style="width:100%" /></el-form-item></el-col>
        <el-col :span="6"><el-form-item label="月费用"><el-input-number v-model="createForm.monthly_fee" :min="0" :controls="false" style="width:100%" /></el-form-item></el-col>
        <el-col :span="6">
          <el-form-item label="到期日">
            <el-date-picker
              v-model="createForm.due_month"
              type="date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              :editable="true"
              placeholder="YYYYMMDD 或 YYMMDD"
              @keydown.enter.capture="commitDateInput((v) => (createForm.due_month = v), $event)"
              @blur.capture="commitDateInput((v) => (createForm.due_month = v), $event)"
            />
          </el-form-item>
        </el-col>
        <el-col :span="6"><el-form-item label="已收金额"><el-input-number v-model="createForm.received_amount" :min="0" :controls="false" style="width:100%" /></el-form-item></el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="付款方式">
            <el-select v-model="createForm.payment_method">
              <el-option label="预收" value="预收" />
              <el-option label="年底收" value="年底收" />
              <el-option label="半年付费" value="半年付费" />
              <el-option label="半年收" value="半年收" />
              <el-option label="后收" value="后收" />
              <el-option label="核定不收费" value="核定不收费" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="台账状态">
            <el-select v-model="createForm.status">
              <el-option label="清账" value="CLEARED" />
              <el-option label="全欠" value="FULL_ARREARS" />
              <el-option label="部分收费" value="PARTIAL" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="代账周期">
        <el-input v-model="createForm.billing_cycle_text" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="createForm.note" type="textarea" :rows="2" />
      </el-form-item>
      <el-form-item label="扩展说明">
        <el-input v-model="createForm.extra_note" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showCreateDialog = false">取消</el-button>
      <el-button type="primary" @click="createRecord">保存</el-button>
    </template>
  </el-dialog>

  <el-drawer
    v-model="showActivityDrawer"
    :title="`催收/收款 - ${selectedRecord?.customer_name ?? ''}`"
    size="min(760px, 92vw)"
  >
    <el-form label-position="top">
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="类型">
            <el-select v-model="activityForm.activity_type" @change="onActivityTypeChange">
              <el-option label="催收" value="REMINDER" />
              <el-option label="收款" value="PAYMENT" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="日期">
            <el-date-picker
              v-model="activityForm.occurred_at"
              type="date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              :editable="true"
              placeholder="YYYYMMDD 或 YYMMDD"
              @keydown.enter.capture="commitDateInput((v) => (activityForm.occurred_at = v), $event)"
              @blur.capture="commitDateInput((v) => (activityForm.occurred_at = v), $event)"
            />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="金额（收款时）">
            <el-input-number
              v-model="activityForm.amount"
              :min="0"
              :controls="false"
              style="width:100%"
            />
            <el-text v-if="!isPaymentActivity" type="info" size="small">
              当前为催收，保存时金额会自动记为 0
            </el-text>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="收款类型">
            <el-select v-model="activityForm.payment_nature" clearable :disabled="!isPaymentActivity">
              <el-option label="月付" value="MONTHLY" />
              <el-option label="年付" value="YEARLY" />
              <el-option label="一次性" value="ONE_OFF" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="下次跟进">
            <el-date-picker
              v-model="activityForm.next_followup_at"
              type="date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              :editable="true"
              placeholder="YYYYMMDD 或 YYMMDD"
              @keydown.enter.capture="commitDateInput((v) => (activityForm.next_followup_at = v), $event)"
              @blur.capture="commitDateInput((v) => (activityForm.next_followup_at = v), $event)"
            />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="结算标记">
            <el-space>
              <el-checkbox v-model="activityForm.is_prepay" :disabled="!isPaymentActivity">
                预付
              </el-checkbox>
              <el-checkbox v-model="activityForm.is_settlement" :disabled="!isPaymentActivity">
                结清
              </el-checkbox>
            </el-space>
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="内容">
        <el-input v-model="activityForm.content" type="textarea" :rows="3" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="activityForm.note" />
      </el-form-item>
      <el-button type="primary" @click="submitActivity">保存日志</el-button>
    </el-form>

    <el-divider />

    <el-table v-loading="activityLoading" :data="activityRows" stripe border>
      <el-table-column prop="occurred_at" label="日期" width="120" />
      <el-table-column label="类型" width="80">
        <template #default="{ row }">
          <el-tag size="small" :type="row.activity_type === 'PAYMENT' ? 'success' : 'warning'">
            {{ activityTypeLabel(row.activity_type) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="amount" label="金额" width="90" />
      <el-table-column
        prop="payment_nature"
        label="性质"
        width="90"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column prop="content" label="内容" min-width="180" show-overflow-tooltip />
      <el-table-column
        prop="next_followup_at"
        label="下次跟进"
        width="120"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        prop="note"
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
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

@media (max-width: 900px) {
  .billing-filter-form {
    display: flex;
    flex-wrap: wrap;
  }
}
</style>
