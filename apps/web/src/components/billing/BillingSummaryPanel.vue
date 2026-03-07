<script setup lang="ts">
import { useResponsive } from "../../composables/useResponsive";
import { statusLabel, statusTagType } from "../../views/billing/viewMeta";

const props = defineProps<{
  summary: {
    total_records: number;
    total_fee: number;
    total_monthly_fee: number;
    status_distribution: Array<{ status: string; count: number }>;
  };
  paymentMethodDistribution: Array<{ payment_method: string; count: number }>;
}>();

const { isMobile } = useResponsive();
</script>

<template>
  <el-space direction="vertical" fill :size="12">
    <div v-if="isMobile" class="summary-grid-mobile">
      <el-card shadow="never" class="summary-mobile-card">
        <div class="summary-mobile-label">记录数</div>
        <div class="summary-mobile-value">{{ props.summary.total_records }}</div>
      </el-card>
      <el-card shadow="never" class="summary-mobile-card">
        <div class="summary-mobile-label">总费用</div>
        <div class="summary-mobile-value">{{ props.summary.total_fee }}</div>
      </el-card>
      <el-card shadow="never" class="summary-mobile-card">
        <div class="summary-mobile-label">月费用</div>
        <div class="summary-mobile-value">{{ props.summary.total_monthly_fee }}</div>
      </el-card>
    </div>
    <el-row v-else :gutter="12">
      <el-col :xs="24" :md="8">
        <el-card shadow="never">
          <el-statistic title="记录数" :value="props.summary.total_records" />
        </el-card>
      </el-col>
      <el-col :xs="24" :md="8">
        <el-card shadow="never">
          <el-statistic title="总费用" :value="props.summary.total_fee" />
        </el-card>
      </el-col>
      <el-col :xs="24" :md="8">
        <el-card shadow="never">
          <el-statistic title="月费用合计" :value="props.summary.total_monthly_fee" />
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
@media (max-width: 420px) {
  .summary-grid-mobile {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
