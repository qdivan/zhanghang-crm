<script setup lang="ts">
import { computed } from "vue";

import FlexibleDateInput from "../shared/FlexibleDateInput.vue";
import type { BillingRecord } from "../../types";
import type { BillingSplitAllocationRow, BillingSplitPaymentForm } from "../../views/billing/forms";
import { paymentStrategyOptions } from "../../views/billing/viewMeta";

const props = defineProps<{
  visible: boolean;
  targetRecord: BillingRecord | null;
  form: BillingSplitPaymentForm;
  allocations: BillingSplitAllocationRow[];
  customerRecordCount: number;
  allocatedTotal: number;
  remainingAmount: number;
  suggestionLoading: boolean;
  submitting: boolean;
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
  "normalize-allocation": [row: BillingSplitAllocationRow];
  "build-suggestions": [];
  submit: [];
}>();

const dialogVisible = computed({
  get: () => props.visible,
  set: (value: boolean) => emit("update:visible", value),
});

const dialogTitle = computed(() => `分摊收款 - ${props.targetRecord?.customer_name ?? ""}`);
</script>

<template>
  <el-dialog v-model="dialogVisible" :title="dialogTitle" width="860px">
    <el-form label-position="top">
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="收款日期">
            <FlexibleDateInput v-model="props.form.occurred_at" :empty-value="''" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="收款总额">
            <el-input-number v-model="props.form.amount" :min="0" :controls="false" style="width:100%" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="优先策略">
            <el-select v-model="props.form.strategy">
              <el-option
                v-for="item in paymentStrategyOptions"
                :key="`split-strategy-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="收款备注">
        <el-input v-model="props.form.note" placeholder="例如：客户按整数付款，按约定优先抵扣到期项目" />
      </el-form-item>
      <el-space>
        <el-button :loading="props.suggestionLoading" @click="emit('build-suggestions')">生成默认分摊建议</el-button>
        <el-text type="info" size="small">支持手动改金额；需保证分摊合计 = 收款总额</el-text>
      </el-space>
    </el-form>

    <el-divider />

    <el-table v-loading="props.suggestionLoading" :data="props.allocations" stripe border>
      <el-table-column prop="serial_no" label="序号" width="80" />
      <el-table-column prop="summary" label="摘要" min-width="180" show-overflow-tooltip />
      <el-table-column prop="due_month" label="到期日" width="110" />
      <el-table-column prop="outstanding_amount" label="当前未收" width="110" />
      <el-table-column label="本次分摊金额" width="170">
        <template #default="{ row }">
          <el-input-number
            v-model="row.allocated_amount"
            :min="0"
            :controls="false"
            style="width:100%"
            @change="emit('normalize-allocation', row)"
          />
        </template>
      </el-table-column>
    </el-table>

    <div class="split-summary">
      <el-text type="info">项目数：{{ props.customerRecordCount }}</el-text>
      <el-text type="info">分摊合计：{{ props.allocatedTotal.toFixed(2) }}</el-text>
      <el-text :type="Math.abs(props.remainingAmount) < 0.01 ? 'success' : 'danger'">
        待分配：{{ props.remainingAmount.toFixed(2) }}
      </el-text>
    </div>

    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="props.submitting" @click="emit('submit')">确认分摊并入账</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.split-summary {
  margin-top: 10px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 14px;
}
</style>
