<script setup lang="ts">
import type { BillingPaymentItem } from "../../types";

const props = defineProps<{
  loading: boolean;
  rows: BillingPaymentItem[];
  unallocatedOnly: boolean;
  canDelete: boolean;
}>();

const emit = defineEmits<{
  "toggle-unallocated": [value: boolean];
  remove: [row: BillingPaymentItem];
  allocate: [row: BillingPaymentItem];
  ledger: [row: BillingPaymentItem];
}>();

function formatAmount(value: number): string {
  const amount = Number(value || 0);
  return amount.toLocaleString("zh-CN", {
    minimumFractionDigits: Number.isInteger(amount) ? 0 : 2,
    maximumFractionDigits: 2,
  });
}

function allocationStatusLabel(row: BillingPaymentItem) {
  if (row.allocation_status === "ALLOCATED") return "已分摊";
  if (row.allocation_status === "PARTIAL") return "部分分摊";
  return row.is_prepay ? "待分摊预收款" : "未分摊";
}

function allocationStatusType(row: BillingPaymentItem): "success" | "warning" | "info" {
  if (row.allocation_status === "ALLOCATED") return "success";
  if (row.allocation_status === "PARTIAL") return "warning";
  return row.is_prepay ? "warning" : "info";
}

function paymentSummary(row: BillingPaymentItem) {
  if ((row.summary || "").trim()) return row.summary;
  if (row.note?.trim()) return row.note.trim();
  return row.is_prepay ? "预收款待分摊" : "收款登记";
}
</script>

<template>
  <el-card shadow="never" class="billing-payments-card">
    <template #header>
      <div class="payments-head">
        <div>
          <div class="payments-title">收款列表</div>
          <div class="payments-copy">这里统一查看收款单、待分摊预收款和入账账户，删除收款单也从这里处理。</div>
        </div>
        <div class="payments-head-actions">
          <el-switch
            :model-value="props.unallocatedOnly"
            inline-prompt
            active-text="仅待分摊"
            inactive-text="全部"
            @update:model-value="emit('toggle-unallocated', $event)"
          />
          <el-tag size="small" type="info" effect="plain">{{ props.rows.length }} 条</el-tag>
        </div>
      </div>
    </template>

    <el-table v-loading="props.loading" :data="props.rows" stripe border size="small" class="payments-table">
      <el-table-column prop="payment_no" label="收款单编号" width="116" />
      <el-table-column prop="occurred_at" label="日期" width="110" />
      <el-table-column label="客户名" min-width="170" fixed="left">
        <template #default="{ row }">
          <div class="payments-customer-cell">
            <el-button link type="primary" @click="emit('ledger', row)">{{ row.customer_name }}</el-button>
            <span class="payments-customer-contact">{{ row.customer_contact_name || "未填联系人" }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="摘要" min-width="220" show-overflow-tooltip>
        <template #default="{ row }">
          <div class="payments-summary-cell">
            <div class="payments-summary-main">{{ paymentSummary(row) }}</div>
            <div v-if="row.note" class="payments-summary-note">{{ row.note }}</div>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="amount" label="金额" width="110" />
      <el-table-column prop="receipt_account" label="入账账户" min-width="150" show-overflow-tooltip />
      <el-table-column label="匹配状态" width="144">
        <template #default="{ row }">
          <div class="payments-status-cell">
            <el-tag size="small" :type="allocationStatusType(row)" effect="plain">
              {{ allocationStatusLabel(row) }}
            </el-tag>
            <div v-if="row.unallocated_amount > 0.01" class="payments-status-note">
              待分摊 {{ formatAmount(row.unallocated_amount) }}
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="accountant_username" label="会计" width="110" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <div class="payments-row-actions">
            <el-button
              v-if="row.unallocated_amount > 0.01"
              link
              type="primary"
              @click="emit('allocate', row)"
            >
              去分摊
            </el-button>
            <el-button v-if="props.canDelete" link type="danger" @click="emit('remove', row)">删除</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<style scoped>
.billing-payments-card {
  border-color: #dfe6e8;
}

.payments-head,
.payments-head-actions,
.payments-row-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.payments-head {
  justify-content: space-between;
  align-items: flex-start;
}

.payments-title {
  font-size: 15px;
  font-weight: 700;
  color: #172330;
}

.payments-copy,
.payments-customer-contact,
.payments-summary-note,
.payments-status-note {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: #667085;
}

.payments-head-actions {
  flex-wrap: wrap;
  justify-content: flex-end;
}

.payments-customer-cell,
.payments-summary-cell,
.payments-status-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.payments-summary-main {
  color: #111827;
}

.payments-row-actions {
  justify-content: flex-start;
}
</style>
