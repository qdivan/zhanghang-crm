<script setup lang="ts">
import { QuestionFilled } from "@element-plus/icons-vue";
import { computed, ref } from "vue";

import type { CustomerListItem } from "../../types";
import { billingStatusOptions, paymentMethodOptions } from "../../utils/billingDraft";
import type { BillingFilters } from "../../views/billing/forms";
import {
  billingMonthHelpLines,
  billingStatusHelpLines,
  paymentMethodHelpLines,
  receiptAccountHelpLines,
} from "../../views/billing/viewMeta";

const props = defineProps<{
  filters: BillingFilters;
  canManageGrant: boolean;
  customers: CustomerListItem[];
  receiptAccountOptions: Array<{ value: string; label: string }>;
}>();

const emit = defineEmits<{
  query: [];
  create: [];
  grant: [];
}>();

const showAdvancedFilters = ref(false);
const hasAdvancedValue = computed(() =>
  Boolean(props.filters.contact_name || props.filters.payment_method || props.filters.status),
);
</script>

<template>
  <el-card shadow="never" class="billing-filter-card">
    <template #header>
      <div class="filter-head">
        <div>
          <div class="filter-title">筛选条件</div>
          <div class="filter-copy">先按客户、账务月份、入账账户定位，再处理收费单和提醒。</div>
        </div>
        <el-button text size="small" @click="showAdvancedFilters = !showAdvancedFilters">
          {{ showAdvancedFilters ? "收起高级筛选" : hasAdvancedValue ? "高级筛选（已选）" : "高级筛选" }}
        </el-button>
      </div>
    </template>

    <el-form inline class="billing-filter-form" @submit.prevent="emit('query')">
      <el-form-item label="关键词">
        <el-input
          v-model="props.filters.keyword"
          placeholder="公司 / 项目 / 备注"
          clearable
          @keyup.enter="emit('query')"
        />
      </el-form-item>
      <el-form-item label="客户">
        <el-select
          v-model="props.filters.customer_id"
          filterable
          clearable
          placeholder="全部客户"
        >
          <el-option
            v-for="item in props.customers"
            :key="`billing-filter-customer-${item.id}`"
            :label="item.name"
            :value="item.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item>
        <template #label>
          <span class="label-with-help">
            账务月份
            <el-tooltip placement="top" :show-after="150">
              <template #content>
                <div v-for="line in billingMonthHelpLines" :key="line">{{ line }}</div>
              </template>
              <el-icon class="help-icon"><QuestionFilled /></el-icon>
            </el-tooltip>
          </span>
        </template>
        <el-date-picker
          v-model="props.filters.billing_month"
          type="month"
          value-format="YYYY-MM"
          format="YYYY-MM"
          placeholder="全部月份"
          clearable
        />
      </el-form-item>
      <el-form-item>
        <template #label>
          <span class="label-with-help">
            入账账户
            <el-tooltip placement="top" :show-after="150">
              <template #content>
                <div v-for="line in receiptAccountHelpLines" :key="line">{{ line }}</div>
              </template>
              <el-icon class="help-icon"><QuestionFilled /></el-icon>
            </el-tooltip>
          </span>
        </template>
        <el-select v-model="props.filters.receipt_account" clearable filterable placeholder="全部账户">
          <el-option
            v-for="item in props.receiptAccountOptions"
            :key="`billing-filter-account-${item.value}`"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>

      <el-form-item v-show="showAdvancedFilters" label="联系人">
        <el-input
          v-model="props.filters.contact_name"
          placeholder="客户联系人"
          clearable
          @keyup.enter="emit('query')"
        />
      </el-form-item>
      <el-form-item v-show="showAdvancedFilters">
        <template #label>
          <span class="label-with-help">
            付款方式
            <el-tooltip placement="top" :show-after="150">
              <template #content>
                <div v-for="line in paymentMethodHelpLines" :key="line">{{ line }}</div>
              </template>
              <el-icon class="help-icon"><QuestionFilled /></el-icon>
            </el-tooltip>
          </span>
        </template>
        <el-select v-model="props.filters.payment_method" placeholder="全部" clearable>
          <el-option
            v-for="item in paymentMethodOptions"
            :key="`filter-method-${item.value}`"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>
      <el-form-item v-show="showAdvancedFilters">
        <template #label>
          <span class="label-with-help">
            台账状态
            <el-tooltip placement="top" :show-after="150">
              <template #content>
                <div v-for="line in billingStatusHelpLines" :key="line">{{ line }}</div>
              </template>
              <el-icon class="help-icon"><QuestionFilled /></el-icon>
            </el-tooltip>
          </span>
        </template>
        <el-select v-model="props.filters.status" placeholder="全部" clearable>
          <el-option
            v-for="item in billingStatusOptions"
            :key="`filter-status-${item.value}`"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>
      <el-form-item class="billing-filter-actions">
        <div class="action-group">
          <el-button size="small" @click="emit('query')">查询</el-button>
          <el-button size="small" type="primary" @click="emit('create')">新增收费单</el-button>
          <el-button v-if="props.canManageGrant" size="small" type="primary" plain @click="emit('grant')">
            数据授权配置
          </el-button>
        </div>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<style scoped>
.billing-filter-card {
  border-color: #dfe6e8;
}

.filter-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.filter-title {
  font-size: 14px;
  font-weight: 700;
  color: #1f2937;
}

.filter-copy {
  margin-top: 2px;
  font-size: 12px;
  line-height: 1.5;
  color: #6b7280;
}

.billing-filter-form {
  display: flex;
  flex-wrap: wrap;
  column-gap: 8px;
}

.billing-filter-form :deep(.el-form-item) {
  margin-right: 8px;
  margin-bottom: 10px;
}

.billing-filter-form :deep(.el-form-item__label) {
  padding-bottom: 3px;
  font-size: 12px;
  color: #5f6f7a;
}

.billing-filter-form :deep(.el-input__wrapper),
.billing-filter-form :deep(.el-select__wrapper),
.billing-filter-form :deep(.el-date-editor.el-input__wrapper) {
  min-height: 34px;
}

.label-with-help {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.help-icon {
  color: #909399;
  font-size: 13px;
  cursor: help;
}

.billing-filter-actions {
  margin-left: auto;
}

.action-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

@media (max-width: 900px) {
  .filter-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .billing-filter-form :deep(.el-form-item) {
    width: 100%;
    margin-right: 0;
  }

  .billing-filter-actions {
    margin-left: 0;
  }

  .action-group {
    display: grid;
    grid-template-columns: 1fr 1fr;
    width: 100%;
  }

  .action-group :deep(.el-button) {
    margin-left: 0;
  }
}
</style>
