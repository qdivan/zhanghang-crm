<script setup lang="ts">
import { MoreFilled } from "@element-plus/icons-vue";

import { useResponsive } from "../../composables/useResponsive";
import type { BillingRecord } from "../../types";
import { statusLabel, statusTagType } from "../../views/billing/viewMeta";

const props = defineProps<{
  loading: boolean;
  rows: BillingRecord[];
  activeCustomerId: number | null;
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

function getDaysUntilDue(dateText: string): number | null {
  const raw = (dateText || "").trim();
  if (!raw) return null;
  const due = new Date(`${raw}T00:00:00`);
  if (Number.isNaN(due.getTime())) return null;
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const diffMs = due.getTime() - today.getTime();
  return Math.round(diffMs / 86400000);
}

function dueReminderText(row: BillingRecord): string {
  const dueDate = (row.due_month || "").trim();
  if (!dueDate) return "-";
  if (row.status === "CLEARED") return `已清账 · ${dueDate}`;
  const days = getDaysUntilDue(dueDate);
  if (days === null) return dueDate;
  if (days < 0) return `已逾期 ${Math.abs(days)} 天`;
  if (days === 0) return "今天到期";
  if (days <= 7) return `${days} 天后到期`;
  return dueDate;
}

function dueReminderTagType(row: BillingRecord): "success" | "warning" | "danger" | "info" {
  if (row.status === "CLEARED") return "success";
  const days = getDaysUntilDue(row.due_month || "");
  if (days === null) return "info";
  if (days < 0) return "danger";
  if (days <= 7) return "warning";
  return "info";
}

function mobileMetrics(row: BillingRecord) {
  return [
    { label: "应收期间", value: row.receivable_period_text || "-" },
    { label: "借方", value: String(row.total_fee) },
    { label: "贷方", value: String(row.received_amount) },
    { label: "余额", value: String(row.outstanding_amount) },
    { label: "到期提醒", value: dueReminderText(row) },
    { label: "入账账户", value: row.latest_receipt_account || "-" },
  ].filter((item) => item.value !== "-");
}

function desktopSummary(row: BillingRecord): string {
  return [row.summary, row.charge_category, row.note].filter(Boolean).join(" · ") || "-";
}

function handleMenuCommand(command: { action: string; row: BillingRecord }) {
  const { action, row } = command;
  if (action === "ledger") emit("ledger", row);
  if (action === "split") emit("split", row);
  if (action === "execution") emit("execution", row);
  if (action === "activity") emit("activity", row);
  if (action === "assignment") emit("assignment", row);
  if (action === "renew") emit("renew", row);
  if (action === "terminate") emit("terminate", row);
}

function billingRowClassName({ row }: { row: BillingRecord }) {
  return props.activeCustomerId && row.customer_id === props.activeCustomerId ? "billing-row-active" : "";
}
</script>

<template>
  <el-card shadow="never" class="billing-records-card">
    <template #header>
      <div class="table-head">
        <div>
          <div class="table-title">收费明细</div>
          <div class="table-subtitle">当前只看收费单、到期提醒、实收与余额；点公司名称可直接展开往来账。</div>
        </div>
        <el-tag size="small" type="success" effect="plain">{{ props.rows.length }} 条</el-tag>
      </div>
    </template>
    <div v-if="isMobile" v-loading="props.loading" class="mobile-record-list">
      <div v-for="row in props.rows" :key="row.id" class="mobile-record-card">
        <div class="mobile-record-head">
          <div class="mobile-record-main">
            <div class="mobile-billing-title">
              <el-tag size="small" effect="plain">#{{ row.serial_no }}</el-tag>
              <el-button
                link
                :type="props.activeCustomerId && row.customer_id === props.activeCustomerId ? 'success' : 'primary'"
                class="mobile-record-title"
                @click="emit('customer', row)"
              >
                {{ row.customer_name }}
              </el-button>
            </div>
            <div class="mobile-record-subtitle">
              {{ row.charge_category || "代账" }} · {{ row.receivable_period_text || "-" }}
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

        <div v-if="desktopSummary(row) !== '-'" class="mobile-record-note">
          {{ desktopSummary(row) }}
        </div>

        <div class="mobile-actions">
          <el-button size="small" @click="emit('ledger', row)">往来账</el-button>
          <el-button size="small" type="primary" :disabled="!props.canWriteRecord(row)" @click="emit('activity', row)">
            催收/收款
          </el-button>
          <el-button size="small" type="warning" @click="emit('execution', row)">执行进度</el-button>
          <el-dropdown trigger="click" @command="handleMenuCommand">
            <el-button size="small" plain>
              更多
              <el-icon><MoreFilled /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
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
    <el-table
      v-else
      v-loading="props.loading"
      :data="props.rows"
      :row-class-name="billingRowClassName"
      stripe
      border
      size="small"
      class="billing-table"
    >
      <el-table-column prop="serial_no" label="序号" width="64" />
      <el-table-column label="公司名称" min-width="150" show-overflow-tooltip>
        <template #default="{ row }">
          <el-button link type="primary" @click="emit('customer', row)">
            <span :class="{ 'active-customer-name': props.activeCustomerId && row.customer_id === props.activeCustomerId }">
              {{ row.customer_name }}
            </span>
          </el-button>
        </template>
      </el-table-column>
      <el-table-column prop="receivable_period_text" label="应收期间" width="146" show-overflow-tooltip />
      <el-table-column label="摘要" min-width="250" show-overflow-tooltip>
        <template #default="{ row }">
          <div class="summary-cell">
            <div class="summary-main">{{ row.summary || row.charge_category || '-' }}</div>
            <div v-if="row.note" class="summary-note">{{ row.note }}</div>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="total_fee" label="借方" width="94" />
      <el-table-column prop="received_amount" label="贷方" width="94" />
      <el-table-column label="到期提醒" width="118">
        <template #default="{ row }">
          <el-tag size="small" :type="dueReminderTagType(row)" effect="plain">
            {{ dueReminderText(row) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="latest_payment_at" label="最近收款" width="112" />
      <el-table-column prop="latest_receipt_account" label="入账账户" width="116" show-overflow-tooltip />
      <el-table-column prop="outstanding_amount" label="余额" width="88" />
      <el-table-column label="状态" width="88">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <div class="table-actions">
            <el-button link type="info" @click="emit('ledger', row)">往来账</el-button>
            <el-button link type="primary" :disabled="!props.canWriteRecord(row)" @click="emit('activity', row)">
              催收/收款
            </el-button>
            <el-button link type="warning" @click="emit('execution', row)">执行进度</el-button>
            <el-dropdown trigger="click" @command="handleMenuCommand">
              <el-button link type="success">
                更多
                <el-icon><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item :command="{ action: 'split', row }" :disabled="!props.canWriteRecord(row)">分摊收款</el-dropdown-item>
                  <el-dropdown-item v-if="props.canManageAssignment" :command="{ action: 'assignment', row }">分派执行</el-dropdown-item>
                  <el-dropdown-item v-if="props.canManageLifecycle" :command="{ action: 'renew', row }">确认续费</el-dropdown-item>
                  <el-dropdown-item v-if="props.canManageLifecycle" :command="{ action: 'terminate', row }">提前终止</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<style scoped>
.billing-records-card {
  border-color: #dfe6e8;
}

.table-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.table-title {
  font-size: 15px;
  font-weight: 700;
  color: #111827;
}

.table-subtitle {
  margin-top: 3px;
  font-size: 12px;
  color: #6b7280;
  line-height: 1.5;
}

.summary-cell {
  line-height: 1.35;
}

.summary-main {
  color: #111827;
}

.summary-note {
  margin-top: 2px;
  font-size: 12px;
  color: #6b7280;
}

.table-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0 10px;
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

.active-customer-name {
  font-weight: 700;
}

.billing-table :deep(.el-table__cell) {
  padding: 8px 0;
}

.billing-table :deep(.el-button.is-link) {
  min-height: auto;
}

:deep(.billing-row-active td) {
  background: #eff6ff !important;
}
</style>
