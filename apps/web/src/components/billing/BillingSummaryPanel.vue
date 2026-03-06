<script setup lang="ts">
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
</script>

<template>
  <el-space direction="vertical" fill :size="12">
    <el-row :gutter="12">
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
