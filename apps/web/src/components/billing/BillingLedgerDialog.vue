<script setup lang="ts">
import { computed } from "vue";

import type { BillingLedgerData, BillingRecord } from "../../types";
import { ledgerSourceLabel } from "../../views/billing/viewMeta";

const props = defineProps<{
  visible: boolean;
  targetRecord: BillingRecord | null;
  loading: boolean;
  dateRange: [string, string] | null;
  hasDateFilter: boolean;
  data: BillingLedgerData | null;
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
  "update:dateRange": [value: [string, string] | null];
  query: [];
  reset: [];
}>();

const dialogVisible = computed({
  get: () => props.visible,
  set: (value: boolean) => emit("update:visible", value),
});

const dateRangeModel = computed({
  get: () => props.dateRange,
  set: (value: [string, string] | null) => emit("update:dateRange", value),
});

const dialogTitle = computed(() => `往来账 - ${props.targetRecord?.customer_name ?? ""}`);
</script>

<template>
  <el-dialog v-model="dialogVisible" :title="dialogTitle" width="960px">
    <el-form inline>
      <el-form-item label="时间范围">
        <el-date-picker
          v-model="dateRangeModel"
          type="daterange"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          format="YYYY-MM-DD"
          unlink-panels
        />
      </el-form-item>
      <el-form-item>
        <el-button :loading="props.loading" @click="emit('query')">查询</el-button>
      </el-form-item>
      <el-form-item>
          <el-button v-if="props.hasDateFilter" text @click="emit('reset')">重置到汇总范围</el-button>
      </el-form-item>
    </el-form>

    <el-row :gutter="12" class="ledger-stats">
      <el-col :span="6">
        <el-card shadow="never">
          <el-statistic title="期初余额" :value="props.data?.opening_balance ?? 0" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never">
          <el-statistic title="应收合计" :value="props.data?.receivable_total ?? 0" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never">
          <el-statistic title="实收合计" :value="props.data?.received_total ?? 0" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never">
          <el-statistic title="期末余额" :value="props.data?.closing_balance ?? props.data?.balance ?? 0" />
        </el-card>
      </el-col>
    </el-row>

    <el-divider content-position="left">客户往来流水</el-divider>
    <el-table v-loading="props.loading" :data="props.data?.entries || []" stripe border>
      <el-table-column prop="occurred_at" label="时间" width="110" />
      <el-table-column prop="summary" label="摘要" min-width="220" show-overflow-tooltip />
      <el-table-column prop="receipt_account" label="入账账户" width="120" />
      <el-table-column label="类型" width="90">
        <template #default="{ row }">
          <el-tag :type="row.source_type === 'PAYMENT' ? 'success' : 'info'" size="small">
            {{ ledgerSourceLabel(row.source_type) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="receivable_amount" label="应收" width="110" />
      <el-table-column prop="received_amount" label="实收" width="110" />
      <el-table-column label="方向" width="80">
        <template #default="{ row }">
          {{ row.source_type === "PAYMENT" ? "平" : "借" }}
        </template>
      </el-table-column>
      <el-table-column prop="balance" label="余额" width="110" />
    </el-table>
  </el-dialog>
</template>

<style scoped>
.ledger-stats {
  margin-bottom: 12px;
}
</style>
