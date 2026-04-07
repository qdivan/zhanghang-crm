<script setup lang="ts">
import { computed } from "vue";

import FlexibleDateInput from "../shared/FlexibleDateInput.vue";
import type { BillingRecord, CustomerListItem } from "../../types";
import type { BillingSplitAllocationRow, BillingSplitPaymentForm } from "../../views/billing/forms";
import { paymentStrategyOptions, receiptAccountOptions } from "../../views/billing/viewMeta";

const props = defineProps<{
  visible: boolean;
  targetRecord: BillingRecord | null;
  customers: CustomerListItem[];
  form: BillingSplitPaymentForm;
  allocations: BillingSplitAllocationRow[];
  customerRecordCount: number;
  allocatedTotal: number;
  remainingAmount: number;
  suggestionLoading: boolean;
  submitting: boolean;
  allocationOnly?: boolean;
  allocationTargetLabel?: string;
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

const resolvedCustomerName = computed(() => {
  if (props.targetRecord?.customer_name) return props.targetRecord.customer_name;
  const matched = props.customers.find((item) => item.id === props.form.customer_id);
  return matched?.name || "";
});

const dialogTitle = computed(() => {
  if (props.allocationOnly) {
    return resolvedCustomerName.value
      ? `预收款分摊 - ${resolvedCustomerName.value}`
      : "预收款分摊";
  }
  return resolvedCustomerName.value ? `收款登记 - ${resolvedCustomerName.value}` : "收款登记";
});
const accountSelectWidth = { width: "100%" };
</script>

<template>
  <el-dialog v-model="dialogVisible" :title="dialogTitle" width="920px">
    <el-form label-position="top">
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="收款单位">
            <el-select
              v-model="props.form.customer_id"
              class="wide-select"
              filterable
              clearable
              placeholder="输入公司名 / 联系人后选择客户"
            >
              <el-option
                v-for="item in props.customers"
                :key="`split-customer-${item.id}`"
                :label="item.contact_name ? `${item.name} / ${item.contact_name}` : item.name"
                :value="item.id"
              />
            </el-select>
          </el-form-item>
        </el-col>
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
            <el-select v-model="props.form.strategy" class="wide-select">
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
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="入账账户">
            <el-select
              v-model="props.form.receipt_account"
              class="wide-select"
              filterable
              allow-create
              default-first-option
              :style="accountSelectWidth"
            >
              <el-option
                v-for="item in receiptAccountOptions"
                :key="`split-account-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="收款性质">
            <el-switch
              v-model="props.form.is_prepay"
              inline-prompt
              active-text="预收款"
              inactive-text="普通收款"
            />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="收款备注">
        <el-input v-model="props.form.note" placeholder="例如：客户按整数付款，按约定优先抵扣到期项目" />
      </el-form-item>
      <el-space>
        <el-button :loading="props.suggestionLoading" @click="emit('build-suggestions')">
          {{ props.allocationOnly ? "匹配未核销应收单" : "匹配应收单" }}
        </el-button>
        <el-text type="info" size="small">
          {{
            props.allocationOnly
              ? `当前正在处理 ${props.allocationTargetLabel || "预收款"}，只需要分配待分摊金额。`
              : props.form.is_prepay
                ? "预收款可以先保存为待分摊，后续再手动分配。"
                : "支持手动改金额；需保证分摊合计 = 收款总额。"
          }}
        </el-text>
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
      <el-button type="primary" :loading="props.submitting" @click="emit('submit')">
        {{ props.allocationOnly ? "确认分摊" : "确认分摊并入账" }}
      </el-button>
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

.wide-select {
  width: 100%;
}

.wide-select :deep(.el-select__wrapper) {
  min-width: 100%;
}
</style>
