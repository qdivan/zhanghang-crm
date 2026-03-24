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
</script>

<template>
  <el-space direction="vertical" fill :size="12">
    <div v-if="isMobile" class="summary-grid-mobile">
      <el-card shadow="never" class="summary-mobile-card">
        <div class="summary-mobile-label">收费单数</div>
        <div class="summary-mobile-value">{{ props.summary.total_records }}</div>
      </el-card>
      <el-card shadow="never" class="summary-mobile-card">
        <div class="summary-mobile-label">应收合计</div>
        <div class="summary-mobile-value">{{ visibleReceivableTotal }}</div>
      </el-card>
      <el-card shadow="never" class="summary-mobile-card">
        <div class="summary-mobile-label">未收合计</div>
        <div class="summary-mobile-value">{{ visibleOutstandingTotal }}</div>
      </el-card>
      <el-card shadow="never" class="summary-mobile-card">
        <div class="summary-mobile-label">7天内到期</div>
        <div class="summary-mobile-value">{{ dueSoonCount }}</div>
      </el-card>
      <el-card shadow="never" class="summary-mobile-card">
        <div class="summary-mobile-label">已逾期</div>
        <div class="summary-mobile-value">{{ overdueCount }}</div>
      </el-card>
    </div>
    <el-row v-else :gutter="12">
      <el-col :xs="24" :md="6">
        <el-card shadow="never">
          <el-statistic title="收费单数" :value="props.summary.total_records" />
        </el-card>
      </el-col>
      <el-col :xs="24" :md="6">
        <el-card shadow="never">
          <el-statistic title="应收合计" :value="visibleReceivableTotal" />
        </el-card>
      </el-col>
      <el-col :xs="24" :md="6">
        <el-card shadow="never">
          <el-statistic title="未收合计" :value="visibleOutstandingTotal" />
        </el-card>
      </el-col>
      <el-col :xs="24" :md="3">
        <el-card shadow="never">
          <el-statistic title="7天内到期" :value="dueSoonCount" />
        </el-card>
      </el-col>
      <el-col :xs="24" :md="3">
        <el-card shadow="never">
          <el-statistic title="已逾期" :value="overdueCount" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="12">
      <el-col :xs="24" :md="12">
        <el-card shadow="never">
          <template #header>付款方式分布</template>
          <el-space wrap>
            <el-tag
              v-for="item in props.paymentMethodDistribution"
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
              v-for="item in props.summary.status_distribution"
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

    <el-card v-if="props.canViewReceiptLedger" shadow="never">
      <template #header>
        <div class="summary-header-row">
          <span>到账账户汇总</span>
          <el-button text type="primary" @click="emit('open-receipt-ledger')">到账核对</el-button>
        </div>
      </template>
      <el-space wrap>
        <el-tag
          v-for="item in props.receiptAccountDistribution"
          :key="item.receipt_account"
          type="success"
          effect="plain"
        >
          {{ item.receipt_account }}：{{ item.payment_count }}笔 / {{ item.total_amount }}
        </el-tag>
      </el-space>
    </el-card>
  </el-space>
</template>

<style scoped>
.summary-grid-mobile {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.summary-mobile-card {
  border-radius: 14px;
}

.summary-mobile-label {
  font-size: 11px;
  color: #6b7280;
}

.summary-mobile-value {
  margin-top: 8px;
  font-size: 20px;
  font-weight: 700;
  line-height: 1.1;
  color: #111827;
}

.summary-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

@media (max-width: 420px) {
  .summary-grid-mobile {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
