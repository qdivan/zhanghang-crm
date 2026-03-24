<script setup lang="ts">
import { computed } from "vue";

import { useResponsive } from "../../composables/useResponsive";
import type { BillingRecord } from "../../types";
import { statusLabel, statusTagType } from "../../views/billing/viewMeta";

const props = defineProps<{
  summary: {
    total_records: number;
    total_fee: number;
    total_monthly_fee: number;
    status_distribution: Array<{ status: string; count: number }>;
  };
  rows: BillingRecord[];
  paymentMethodDistribution: Array<{ payment_method: string; count: number }>;
  receiptAccountDistribution: Array<{ receipt_account: string; payment_count: number; total_amount: number }>;
  canViewReceiptLedger: boolean;
}>();

const emit = defineEmits<{
  "open-receipt-ledger": [];
}>();

const { isMobile } = useResponsive();

function getDaysUntilDue(dateText: string): number | null {
  const raw = (dateText || "").trim();
  if (!raw) return null;
  const due = new Date(`${raw}T00:00:00`);
  if (Number.isNaN(due.getTime())) return null;
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((due.getTime() - today.getTime()) / 86400000);
}

const visibleReceivableTotal = computed(() =>
  props.rows.reduce((sum, item) => sum + Number(item.total_fee || 0), 0),
);

const visibleOutstandingTotal = computed(() =>
  props.rows.reduce((sum, item) => sum + Number(item.outstanding_amount || 0), 0),
);

const dueSoonCount = computed(() =>
  props.rows.filter((item) => {
    if (Number(item.outstanding_amount || 0) <= 0) return false;
    const days = getDaysUntilDue(item.due_month || "");
    return days !== null && days >= 0 && days <= 7;
  }).length,
);

const overdueCount = computed(() =>
  props.rows.filter((item) => {
    if (Number(item.outstanding_amount || 0) <= 0) return false;
    const days = getDaysUntilDue(item.due_month || "");
    return days !== null && days < 0;
  }).length,
);

const summaryCards = computed(() => [
  { label: "收费单数", value: props.summary.total_records },
  { label: "应收合计", value: visibleReceivableTotal.value },
  { label: "未收合计", value: visibleOutstandingTotal.value, accent: true },
  { label: "7天内到期", value: dueSoonCount.value },
  { label: "已逾期", value: overdueCount.value, danger: true },
]);
</script>

<template>
  <section class="summary-panel">
    <div class="summary-strip" :class="{ mobile: isMobile }">
      <article
        v-for="item in summaryCards"
        :key="item.label"
        class="summary-stat"
        :class="{ accent: item.accent, danger: item.danger }"
      >
        <span class="summary-stat-label">{{ item.label }}</span>
        <strong class="summary-stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <div class="summary-grid" :class="{ mobile: isMobile }">
      <section class="summary-block">
        <div class="summary-block-head">
          <span>付款方式</span>
          <small>{{ props.paymentMethodDistribution.length }}项</small>
        </div>
        <div class="summary-tag-list">
          <el-tag
            v-for="item in props.paymentMethodDistribution"
            :key="item.payment_method"
            size="small"
            type="info"
            effect="plain"
          >
            {{ item.payment_method }} · {{ item.count }}
          </el-tag>
        </div>
      </section>

      <section class="summary-block">
        <div class="summary-block-head">
          <span>台账状态</span>
          <small>{{ props.summary.status_distribution.length }}项</small>
        </div>
        <div class="summary-tag-list">
          <el-tag
            v-for="item in props.summary.status_distribution"
            :key="item.status"
            size="small"
            :type="statusTagType(item.status)"
            effect="plain"
          >
            {{ statusLabel(item.status) }} · {{ item.count }}
          </el-tag>
        </div>
      </section>

      <section v-if="props.canViewReceiptLedger" class="summary-block receipt-block">
        <div class="summary-block-head with-action">
          <div>
            <span>到账账户</span>
            <small>{{ props.receiptAccountDistribution.length }}项</small>
          </div>
          <el-button text size="small" type="primary" @click="emit('open-receipt-ledger')">到账核对</el-button>
        </div>
        <div class="summary-tag-list">
          <el-tag
            v-for="item in props.receiptAccountDistribution"
            :key="item.receipt_account"
            size="small"
            type="success"
            effect="plain"
          >
            {{ item.receipt_account }} · {{ item.payment_count }}笔 / {{ item.total_amount }}
          </el-tag>
        </div>
      </section>
    </div>
  </section>
</template>

<style scoped>
.summary-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.summary-strip {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}

.summary-strip.mobile {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.summary-stat {
  padding: 12px 14px;
  border: 1px solid #dfe6e8;
  background: #ffffff;
}

.summary-stat.accent {
  background: #f8fbfb;
}

.summary-stat.danger {
  background: #fff8f8;
}

.summary-stat-label {
  display: block;
  font-size: 12px;
  color: #6b7280;
}

.summary-stat-value {
  display: block;
  margin-top: 8px;
  font-size: 24px;
  line-height: 1;
  color: #172330;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.summary-grid.mobile {
  grid-template-columns: 1fr;
}

.summary-block {
  border: 1px solid #dfe6e8;
  background: #ffffff;
  padding: 12px 14px;
}

.summary-block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 600;
  color: #1f2937;
}

.summary-block-head small {
  font-size: 11px;
  font-weight: 500;
  color: #6b7280;
}

.summary-block-head.with-action {
  align-items: flex-start;
}

.summary-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

@media (max-width: 900px) {
  .summary-stat {
    padding: 10px 12px;
  }

  .summary-stat-value {
    font-size: 20px;
  }
}

@media (max-width: 480px) {
  .summary-strip.mobile {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
