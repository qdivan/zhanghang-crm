<script setup lang="ts">
import type { BillingRecord } from "../../types";
import { normalizePaymentMethod, statusLabel, statusTagType } from "../../views/billing/viewMeta";

const props = defineProps<{
  loading: boolean;
  rows: BillingRecord[];
  canManageAssignment: boolean;
  canManageLifecycle: boolean;
  canWriteRecord: (row: BillingRecord) => boolean;
}>();

const emit = defineEmits<{
  customer: [row: BillingRecord];
  ledger: [row: BillingRecord];
  split: [row: BillingRecord];
  execution: [row: BillingRecord];
  activity: [row: BillingRecord];
  assignment: [row: BillingRecord];
  renew: [row: BillingRecord];
  terminate: [row: BillingRecord];
}>();
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="table-head">
        <span>收费主台账（对齐 `周 (2)`）</span>
        <el-tag type="success" effect="plain">{{ props.rows.length }} 条</el-tag>
      </div>
    </template>
    <el-table v-loading="props.loading" :data="props.rows" stripe border>
      <el-table-column prop="serial_no" label="序号" width="70" />
      <el-table-column label="名称" min-width="120" show-overflow-tooltip>
        <template #default="{ row }">
          <el-button link type="primary" @click="emit('customer', row)">
            {{ row.customer_name }}
          </el-button>
        </template>
      </el-table-column>
      <el-table-column
        prop="contact_name"
        label="联系人"
        width="110"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        prop="charge_category"
        label="收费类别"
        width="110"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        label="计费"
        width="80"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      >
        <template #default="{ row }">
          {{ row.charge_mode === "ONE_TIME" ? "按次" : "按期" }}
        </template>
      </el-table-column>
      <el-table-column
        label="金额口径"
        width="100"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      >
        <template #default="{ row }">
          {{
            row.amount_basis === "YEARLY"
              ? "年费"
              : row.amount_basis === "PERIOD_TOTAL"
                ? "周期总价"
                : row.amount_basis === "ONE_TIME"
                  ? "单次费用"
                  : "月费"
          }}
        </template>
      </el-table-column>
      <el-table-column
        prop="accountant_username"
        label="会计"
        width="100"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        prop="total_fee"
        label="总费用"
        width="90"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        prop="received_amount"
        label="已收"
        width="85"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column prop="outstanding_amount" label="未收" width="80" />
      <el-table-column
        label="状态"
        width="90"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      >
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column
        prop="monthly_fee"
        label="月度参考"
        width="85"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        prop="billing_cycle_text"
        label="周期说明"
        min-width="170"
        show-overflow-tooltip
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        prop="due_month"
        label="到期日"
        width="100"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        prop="summary"
        label="摘要"
        min-width="130"
        show-overflow-tooltip
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        prop="collection_start_date"
        label="服务开始"
        width="108"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        label="付款方式"
        width="110"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      >
        <template #default="{ row }">
          {{ normalizePaymentMethod(row.payment_method) }}
        </template>
      </el-table-column>
      <el-table-column
        prop="note"
        label="备注"
        min-width="160"
        show-overflow-tooltip
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        prop="extra_note"
        label="扩展"
        min-width="120"
        show-overflow-tooltip
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column label="操作" width="560">
        <template #default="{ row }">
          <el-space>
            <el-button link type="info" @click="emit('ledger', row)">明细账</el-button>
            <el-button link type="success" :disabled="!props.canWriteRecord(row)" @click="emit('split', row)">
              分摊收款
            </el-button>
            <el-button link type="warning" @click="emit('execution', row)">执行进度</el-button>
            <el-button link type="primary" :disabled="!props.canWriteRecord(row)" @click="emit('activity', row)">
              催收/收款
            </el-button>
            <el-button v-if="props.canManageAssignment" link type="success" @click="emit('assignment', row)">
              分派执行
            </el-button>
            <el-button v-if="props.canManageLifecycle" link type="primary" @click="emit('renew', row)">
              续费+1年
            </el-button>
            <el-button v-if="props.canManageLifecycle" link type="danger" @click="emit('terminate', row)">
              提前终止
            </el-button>
          </el-space>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<style scoped>
.table-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
