<script setup lang="ts">
import { QuestionFilled } from "@element-plus/icons-vue";

import { billingStatusOptions, paymentMethodOptions } from "../../utils/billingDraft";
import type { BillingFilters } from "../../views/billing/forms";
import { billingStatusHelpLines, paymentMethodHelpLines } from "../../views/billing/viewMeta";

const props = defineProps<{
  filters: BillingFilters;
  canManageGrant: boolean;
}>();

const emit = defineEmits<{
  query: [];
  create: [];
  grant: [];
}>();
</script>

<template>
  <el-card shadow="never">
    <el-form inline @submit.prevent="emit('query')" class="billing-filter-form">
      <el-form-item label="关键词">
        <el-input
          v-model="props.filters.keyword"
          placeholder="序号/客户/联系人/备注"
          clearable
          @keyup.enter="emit('query')"
        />
      </el-form-item>
      <el-form-item label="联系人">
        <el-input
          v-model="props.filters.contact_name"
          placeholder="客户联系人"
          clearable
          @keyup.enter="emit('query')"
        />
      </el-form-item>
      <el-form-item>
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
      <el-form-item>
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
      <el-form-item>
        <el-button @click="emit('query')">查询</el-button>
        <el-button type="primary" @click="emit('create')">新增收费记录</el-button>
        <el-button v-if="props.canManageGrant" type="primary" plain @click="emit('grant')">数据授权配置</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<style scoped>
.label-with-help {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.help-icon {
  color: #909399;
  font-size: 14px;
  cursor: help;
}

@media (max-width: 900px) {
  .billing-filter-form {
    display: flex;
    flex-wrap: wrap;
  }
}
</style>
