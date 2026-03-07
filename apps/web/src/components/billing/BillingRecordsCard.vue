<script setup lang="ts">
import { MoreFilled } from "@element-plus/icons-vue";

import { useResponsive } from "../../composables/useResponsive";
import type { BillingRecord } from "../../types";
import { normalizePaymentMethod, statusLabel, statusTagType } from "../../views/billing/viewMeta";

const props = defineProps<{
  loading: boolean;
  rows: BillingRecord[];
  canManageAssignment: boolean;
  canManageLifecycle: boolean;
  canWriteRecord: (row: BillingRecord) => boolean;
}>();

const emit = defineEmits<{
  customer: [row: BillingRecord];
  ledger: [row: BillingRecord];
  split: [row: BillingRecord];
  execution: [row: BillingRecord];
  activity: [row: BillingRecord];
  assignment: [row: BillingRecord];
  renew: [row: BillingRecord];
  terminate: [row: BillingRecord];
}>();

const { isMobile } = useResponsive();

function mobileMetrics(row: BillingRecord) {
  return [
    { label: "未收", value: String(row.outstanding_amount) },
    { label: "总费用", value: String(row.total_fee) },
    { label: "到期日", value: row.due_month || "-" },
    { label: "负责会计", value: row.accountant_username || "-" },
    { label: "付款方式", value: normalizePaymentMethod(row.payment_method) },
  ].filter((item) => item.value !== "-");
}

function handleMobileCommand(command: string, row: BillingRecord) {
  if (command === "customer") emit("customer", row);
  if (command === "ledger") emit("ledger", row);
  if (command === "split") emit("split", row);
  if (command === "execution") emit("execution", row);
  if (command === "activity") emit("activity", row);
  if (command === "assignment") emit("assignment", row);
  if (command === "renew") emit("renew", row);
  if (command === "terminate") emit("terminate", row);
}

function onMobileMenuCommand(command: { action: string; row: BillingRecord }) {
  handleMobileCommand(command.action, command.row);
}
</script>

<template>
  <el-card shadow="never">
    <template #header>
        <div class="table-head">
        <span>{{ isMobile ? "收费主台账" : "收费主台账（对齐 `周 (2)`）" }}</span>
        <el-tag type="success" effect="plain">{{ props.rows.length }} 条</el-tag>
      </div>
    </template>
    <div v-if="isMobile" v-loading="props.loading" class="mobile-record-list">
      <div v-for="row in props.rows" :key="row.id" class="mobile-record-card">
        <div class="mobile-record-head">
          <div class="mobile-record-main">
            <div class="mobile-billing-title">
              <el-tag size="small" effect="plain">#{{ row.serial_no }}</el-tag>
              <el-button link type="primary" class="mobile-record-title" @click="emit('customer', row)">
                {{ row.customer_name }}
              </el-button>
            </div>
            <div class="mobile-record-subtitle">
              {{ row.charge_category || "代账" }} ·
              {{ row.charge_mode === "ONE_TIME" ? "按次" : "按期" }} ·
              {{ normalizePaymentMethod(row.payment_method) }}
            </div>
          </div>
          <el-tag :type="statusTagType(row.status)" size="small">
            {{ statusLabel(row.status) }}
          </el-tag>
        </div>

        <div class="mobile-record-metrics">
          <div v-for="item in mobileMetrics(row)" :key="`${row.id}-${item.label}`" class="mobile-metric">
            <div class="mobile-metric-label">{{ item.label }}</div>
            <div class="mobile-metric-value">{{ item.value }}</div>
          </div>
        </div>

        <div v-if="row.summary || row.note" class="mobile-record-note">
          <div v-if="row.summary">摘要：{{ row.summary }}</div>
          <div v-if="row.note">备注：{{ row.note }}</div>
        </div>

        <div class="mobile-actions">
          <el-button size="small" @click="emit('ledger', row)">明细账</el-button>
          <el-button size="small" type="primary" :disabled="!props.canWriteRecord(row)" @click="emit('activity', row)">
            催收/收款
          </el-button>
          <el-button size="small" type="warning" @click="emit('execution', row)">执行进度</el-button>
          <el-dropdown trigger="click" @command="onMobileMenuCommand">
            <el-button size="small" plain>
              更多
              <el-icon><MoreFilled /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item :command="{ action: 'customer', row }">客户档案</el-dropdown-item>
                <el-dropdown-item :command="{ action: 'split', row }" :disabled="!props.canWriteRecord(row)">分摊收款</el-dropdown-item>
                <el-dropdown-item v-if="props.canManageAssignment" :command="{ action: 'assignment', row }">分派执行</el-dropdown-item>
                <el-dropdown-item v-if="props.canManageLifecycle" :command="{ action: 'renew', row }">确认续费</el-dropdown-item>
                <el-dropdown-item v-if="props.canManageLifecycle" :command="{ action: 'terminate', row }">提前终止</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </div>
    <el-table v-else v-loading="props.loading" :data="props.rows" stripe border>
      <el-table-column prop="serial_no" label="序号" width="70" />
      <el-table-column label="名称" min-width="120" show-overflow-tooltip>
        <template #default="{ row }">
          <el-button link type="primary" @click="emit('customer', row)">
            {{ row.customer_name }}
          </el-button>
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
        prop="charge_category"
        label="收费类别"
        width="110"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        label="计费"
        width="80"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      >
        <template #default="{ row }">
          {{ row.charge_mode === "ONE_TIME" ? "按次" : "按期" }}
        </template>
      </el-table-column>
      <el-table-column
        label="金额口径"
        width="100"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      >
        <template #default="{ row }">
          {{
            row.amount_basis === "YEARLY"
              ? "年费"
              : row.amount_basis === "PERIOD_TOTAL"
                ? "周期总价"
                : row.amount_basis === "ONE_TIME"
                  ? "单次费用"
                  : "月费"
          }}
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
        label="月度参考"
        width="85"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        prop="billing_cycle_text"
        label="周期说明"
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
        prop="summary"
        label="摘要"
        min-width="130"
        show-overflow-tooltip
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        prop="collection_start_date"
        label="服务开始"
        width="108"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        label="付款方式"
        width="110"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      >
        <template #default="{ row }">
          {{ normalizePaymentMethod(row.payment_method) }}
        </template>
      </el-table-column>
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
      <el-table-column label="操作" width="560">
        <template #default="{ row }">
          <el-space>
            <el-button link type="info" @click="emit('ledger', row)">明细账</el-button>
            <el-button link type="success" :disabled="!props.canWriteRecord(row)" @click="emit('split', row)">
              分摊收款
            </el-button>
            <el-button link type="warning" @click="emit('execution', row)">执行进度</el-button>
            <el-button link type="primary" :disabled="!props.canWriteRecord(row)" @click="emit('activity', row)">
              催收/收款
            </el-button>
            <el-button v-if="props.canManageAssignment" link type="success" @click="emit('assignment', row)">
              分派执行
            </el-button>
            <el-button v-if="props.canManageLifecycle" link type="primary" @click="emit('renew', row)">
              续费+1年
            </el-button>
            <el-button v-if="props.canManageLifecycle" link type="danger" @click="emit('terminate', row)">
              提前终止
            </el-button>
          </el-space>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<style scoped>
.table-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.mobile-billing-title {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.mobile-actions :deep(.el-button) {
  margin-left: 0;
}
</style>
