<script setup lang="ts">
import { computed } from "vue";

import { useResponsive } from "../../composables/useResponsive";
import FlexibleDateInput from "../shared/FlexibleDateInput.vue";
import type { BillingActivity, BillingRecord } from "../../types";
import type { BillingActivityForm } from "../../views/billing/forms";
import {
  activityTypeLabel,
  isPaymentActivityType,
  receiptAccountOptions,
} from "../../views/billing/viewMeta";

const props = defineProps<{
  visible: boolean;
  targetRecord: BillingRecord | null;
  form: BillingActivityForm;
  loading: boolean;
  rows: BillingActivity[];
  queueLabel?: string;
  showNextAction?: boolean;
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
  "activity-type-change": [value: unknown];
  submit: [];
  "submit-next": [];
}>();

const drawerVisible = computed({
  get: () => props.visible,
  set: (value: boolean) => emit("update:visible", value),
});

const drawerTitle = computed(() => `催收/收款 - ${props.targetRecord?.customer_name ?? ""}`);
const isPaymentActivity = computed(() => isPaymentActivityType(props.form.activity_type));
const { isMobile } = useResponsive();
</script>

<template>
  <el-drawer v-model="drawerVisible" :title="drawerTitle" size="min(760px, 92vw)">
    <div v-if="props.queueLabel" class="mobile-queue-panel">
      <div>
        <div class="mobile-queue-kicker">连续催收</div>
        <div class="mobile-queue-copy">当前处理 {{ props.queueLabel }}，保存后可直接切下一条。</div>
      </div>
      <strong>{{ props.queueLabel }}</strong>
    </div>
    <el-form label-position="top">
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="类型">
            <el-select v-model="props.form.activity_type" @change="emit('activity-type-change', $event)">
              <el-option label="催收" value="REMINDER" />
              <el-option label="收款" value="PAYMENT" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="日期">
            <FlexibleDateInput v-model="props.form.occurred_at" :empty-value="''" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="金额（收款时）">
            <el-input-number v-model="props.form.amount" :min="0" :controls="false" style="width:100%" />
            <el-text v-if="!isPaymentActivity" type="info" size="small">
              当前为催收，保存时金额会自动记为 0
            </el-text>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="收款类型">
            <el-select v-model="props.form.payment_nature" clearable :disabled="!isPaymentActivity">
              <el-option label="月付" value="MONTHLY" />
              <el-option label="年付" value="YEARLY" />
              <el-option label="一次性" value="ONE_OFF" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="下次跟进">
            <FlexibleDateInput v-model="props.form.next_followup_at" clearable />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="入账账户">
            <el-select
              v-model="props.form.receipt_account"
              filterable
              allow-create
              default-first-option
              :disabled="!isPaymentActivity"
            >
              <el-option
                v-for="item in receiptAccountOptions"
                :key="`receipt-account-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="12">
        <el-col :span="24">
          <el-form-item label="结算标记">
            <el-space>
              <el-checkbox v-model="props.form.is_prepay" :disabled="!isPaymentActivity">预付</el-checkbox>
              <el-checkbox v-model="props.form.is_settlement" :disabled="!isPaymentActivity">结清</el-checkbox>
            </el-space>
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="内容">
        <el-input v-model="props.form.content" type="textarea" :rows="3" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="props.form.note" />
      </el-form-item>
      <el-space wrap>
        <el-button type="primary" @click="emit('submit')">保存日志</el-button>
        <el-button v-if="props.showNextAction" plain @click="emit('submit-next')">保存并下一条</el-button>
      </el-space>
    </el-form>

    <el-divider />

    <div v-if="isMobile" v-loading="props.loading" class="mobile-record-list">
      <div v-for="row in props.rows" :key="row.id" class="mobile-record-card">
        <div class="mobile-record-head">
          <div class="mobile-record-main">
            <div class="mobile-record-title">{{ row.occurred_at }}</div>
            <div class="mobile-record-subtitle">
              {{ activityTypeLabel(row.activity_type) }} · {{ row.actor_username || "-" }} · 金额 {{ row.amount }}
            </div>
          </div>
        </div>
        <div class="detail-long-fields">
          <div v-if="row.receipt_account" class="detail-long-field">
            <div class="detail-long-label">入账账户</div>
            <div class="detail-long-value">{{ row.receipt_account }}</div>
          </div>
          <div class="detail-long-field">
            <div class="detail-long-label">内容</div>
            <div class="detail-long-value">{{ row.content || "-" }}</div>
          </div>
          <div class="detail-long-field">
            <div class="detail-long-label">备注</div>
            <div class="detail-long-value">{{ row.note || "-" }}</div>
          </div>
        </div>
      </div>
    </div>
    <el-table v-else v-loading="props.loading" :data="props.rows" stripe border>
      <el-table-column prop="occurred_at" label="日期" width="120" />
      <el-table-column label="类型" width="80">
        <template #default="{ row }">
          <el-tag size="small" :type="row.activity_type === 'PAYMENT' ? 'success' : 'warning'">
            {{ activityTypeLabel(row.activity_type) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="amount" label="金额" width="90" />
      <el-table-column prop="receipt_account" label="入账账户" width="180" show-overflow-tooltip />
      <el-table-column prop="actor_username" label="记录人" width="100" />
      <el-table-column
        prop="payment_nature"
        label="性质"
        width="90"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column prop="content" label="内容" min-width="180" show-overflow-tooltip />
      <el-table-column
        prop="next_followup_at"
        label="下次跟进"
        width="120"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        prop="note"
        label="备注"
        min-width="130"
        show-overflow-tooltip
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
    </el-table>
  </el-drawer>
</template>

<style scoped>
.detail-long-fields {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.detail-long-field {
  border-top: 1px solid #eef2f7;
  padding-top: 10px;
}

.detail-long-label {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 4px;
}

.detail-long-value {
  font-size: 13px;
  line-height: 1.6;
  color: #111827;
  word-break: break-word;
}
</style>
