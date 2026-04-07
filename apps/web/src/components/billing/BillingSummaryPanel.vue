<script setup lang="ts">
import { computed } from "vue";

import type { BillingCustomerSummaryItem, BillingSummaryData } from "../../types";

const props = defineProps<{
  summary: BillingSummaryData;
  loading: boolean;
  dateRange: [string, string] | null;
  paymentMethodDistribution: Array<{ payment_method: string; count: number }>;
  receiptAccountDistribution: Array<{ receipt_account: string; payment_count: number; total_amount: number }>;
  canViewReceiptLedger: boolean;
}>();

const emit = defineEmits<{
  "update:dateRange": [value: [string, string] | null];
  "query-summary": [];
  "open-receipt-ledger": [];
  "open-payment": [row?: BillingCustomerSummaryItem];
  "open-payment-list": [];
  "open-customer-ledger": [row: BillingCustomerSummaryItem];
}>();

const dateRangeModel = computed({
  get: () => props.dateRange,
  set: (value: [string, string] | null) => emit("update:dateRange", value),
});

function formatAmount(value: number): string {
  const amount = Number(value || 0);
  return amount.toLocaleString("zh-CN", {
    minimumFractionDigits: Number.isInteger(amount) ? 0 : 2,
    maximumFractionDigits: 2,
  });
}

const outstandingTotal = computed(() =>
  props.summary.customer_summaries.reduce((sum, item) => sum + Number(item.ending_outstanding || 0), 0),
);

const summaryCards = computed(() => [
  {
    label: "期末未收",
    value: formatAmount(outstandingTotal.value),
    hint: `${props.summary.customer_summaries.length} 个客户`,
    tone: "danger",
  },
  {
    label: "本期应收",
    value: formatAmount(
      props.summary.customer_summaries.reduce((sum, item) => sum + Number(item.period_receivable || 0), 0),
    ),
    hint: props.summary.summary_date_from && props.summary.summary_date_to
      ? `${props.summary.summary_date_from} 至 ${props.summary.summary_date_to}`
      : "当前查询范围",
    tone: "primary",
  },
  {
    label: "本期实收",
    value: formatAmount(
      props.summary.customer_summaries.reduce((sum, item) => sum + Number(item.period_received || 0), 0),
    ),
    hint: `收费单 ${props.summary.total_records} 条`,
    tone: "success",
  },
]);
</script>

<template>
  <el-card shadow="never" class="billing-summary-card">
    <template #header>
      <div class="summary-head">
        <div>
          <div class="summary-title">收费明细总览</div>
          <div class="summary-copy">先看客户维度的期初欠款、本期应收、本期实收和期末未收，再下钻到客户往来账。</div>
        </div>
        <div class="summary-actions">
          <el-button class="billing-primary-action" type="primary" size="large" @click="emit('open-payment')">
            收款
          </el-button>
          <el-button size="small" plain @click="emit('open-payment-list')">收款列表</el-button>
          <el-button v-if="props.canViewReceiptLedger" size="small" plain @click="emit('open-receipt-ledger')">
            到账核对
          </el-button>
        </div>
      </div>
    </template>

    <el-form inline class="summary-filter-form" @submit.prevent="emit('query-summary')">
      <el-form-item label="汇总时间范围">
        <el-date-picker
          v-model="dateRangeModel"
          type="daterange"
          value-format="YYYY-MM-DD"
          format="YYYY-MM-DD"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          unlink-panels
        />
      </el-form-item>
      <el-form-item>
        <el-button :loading="props.loading" type="primary" @click="emit('query-summary')">刷新汇总</el-button>
      </el-form-item>
    </el-form>

    <div class="summary-stat-grid">
      <article v-for="item in summaryCards" :key="item.label" class="summary-stat-card" :class="item.tone">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <small>{{ item.hint }}</small>
      </article>
    </div>

    <div class="summary-meta-grid">
      <div class="summary-meta-block">
        <div class="summary-meta-title">付款方式</div>
        <div class="summary-meta-tags">
          <el-tag
            v-for="item in props.paymentMethodDistribution"
            :key="`method-${item.payment_method}`"
            size="small"
            effect="plain"
          >
            {{ item.payment_method }} {{ item.count }}
          </el-tag>
          <span v-if="!props.paymentMethodDistribution.length" class="summary-empty-text">暂无统计</span>
        </div>
      </div>
      <div class="summary-meta-block">
        <div class="summary-meta-title">入账账户</div>
        <div class="summary-account-list">
          <div
            v-for="item in props.receiptAccountDistribution.slice(0, 4)"
            :key="`account-${item.receipt_account}`"
            class="summary-account-item"
          >
            <span>{{ item.receipt_account }}</span>
            <strong>{{ formatAmount(item.total_amount) }}</strong>
          </div>
          <span v-if="!props.receiptAccountDistribution.length" class="summary-empty-text">当前范围内暂无入账账户分布</span>
        </div>
      </div>
    </div>

    <el-table v-loading="props.loading" :data="props.summary.customer_summaries" stripe border size="small" class="summary-customer-table">
      <el-table-column label="客户名称" min-width="180" fixed="left">
        <template #default="{ row }">
          <div class="summary-customer-main">
            <el-button link type="primary" @click="emit('open-customer-ledger', row)">{{ row.customer_name }}</el-button>
            <span class="summary-customer-contact">{{ row.customer_contact_name || "未填联系人" }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="opening_arrears" label="期初欠款" width="118" />
      <el-table-column prop="period_receivable" label="本期应收" width="118" />
      <el-table-column prop="period_received" label="本期实收" width="118" />
      <el-table-column prop="ending_outstanding" label="期末未收" width="118" />
      <el-table-column label="逾期提醒" width="98">
        <template #default="{ row }">
          <el-tag :type="row.overdue_count > 0 ? 'danger' : 'success'" size="small" effect="plain">
            {{ row.overdue_count > 0 ? `${row.overdue_count} 条逾期` : "正常" }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="最近催收/跟进" min-width="260" show-overflow-tooltip>
        <template #default="{ row }">
          <div class="summary-activity-cell">
            <span>{{ row.latest_activity_content || "暂无记录" }}</span>
            <small>{{ row.latest_activity_at || "-" }}</small>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <div class="summary-row-actions">
            <el-button link type="primary" @click="emit('open-customer-ledger', row)">往来账</el-button>
            <el-button link type="success" @click="emit('open-payment', row)">收款</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<style scoped>
.billing-summary-card {
  border-color: #dfe6e8;
}

.summary-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.summary-title {
  font-size: 18px;
  font-weight: 700;
  color: #172330;
}

.summary-copy {
  margin-top: 4px;
  max-width: 720px;
  font-size: 13px;
  line-height: 1.6;
  color: #61727e;
}

.summary-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.billing-primary-action {
  min-width: 104px;
  font-weight: 700;
}

.summary-filter-form {
  margin-bottom: 12px;
}

.summary-filter-form :deep(.el-form-item__label) {
  color: #5f6f7a;
}

.summary-filter-form :deep(.el-input__wrapper),
.summary-filter-form :deep(.el-select__wrapper),
.summary-filter-form :deep(.el-date-editor.el-input__wrapper) {
  min-height: 36px;
  min-width: 280px;
}

.summary-stat-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.summary-stat-card {
  padding: 14px 16px;
  border: 1px solid #dde5e7;
  background: #f8fbfb;
}

.summary-stat-card span,
.summary-stat-card small {
  display: block;
}

.summary-stat-card span {
  font-size: 12px;
  color: #6c7b87;
}

.summary-stat-card strong {
  display: block;
  margin-top: 8px;
  font-size: 24px;
  line-height: 1;
  color: #172330;
}

.summary-stat-card small {
  margin-top: 6px;
  font-size: 12px;
  color: #74828d;
}

.summary-stat-card.danger {
  border-top: 3px solid #dc2626;
}

.summary-stat-card.primary {
  border-top: 3px solid #2563eb;
}

.summary-stat-card.success {
  border-top: 3px solid #16a34a;
}

.summary-meta-grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 12px;
  margin-bottom: 14px;
}

.summary-meta-block {
  padding: 12px 14px;
  border: 1px solid #dde5e7;
  background: #ffffff;
}

.summary-meta-title {
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 600;
  color: #1f2937;
}

.summary-meta-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.summary-account-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.summary-account-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
  color: #1f2937;
}

.summary-empty-text {
  font-size: 12px;
  color: #8a98a3;
}

.summary-customer-table {
  width: 100%;
}

.summary-customer-main {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.summary-customer-contact,
.summary-activity-cell small {
  font-size: 12px;
  color: #7b8794;
}

.summary-activity-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-row-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

@media (max-width: 1200px) {
  .summary-stat-grid,
  .summary-meta-grid {
    grid-template-columns: 1fr;
  }
}
</style>
