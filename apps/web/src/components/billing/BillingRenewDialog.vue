<script setup lang="ts">
import BillingDraftRowsEditor from "../BillingDraftRowsEditor.vue";
import type { BillingCreatePayload, BillingRecord } from "../../types";

const props = defineProps<{
  visible: boolean;
  targetRecord: BillingRecord | null;
  rows: BillingCreatePayload[];
  loading: boolean;
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
  "update:rows": [value: BillingCreatePayload[]];
  closed: [];
  submit: [];
}>();
</script>

<template>
  <el-dialog
    :model-value="props.visible"
    :title="`确认续费 - ${props.targetRecord?.customer_name ?? ''}`"
    width="760px"
    @update:model-value="emit('update:visible', $event)"
    @closed="emit('closed')"
  >
    <el-space direction="vertical" fill :size="12">
      <el-alert
        type="info"
        :closable="false"
        title="系统已复制上一期收费内容并顺延 12 个月。请先核对金额、开始月份、结束月份，再确认生成。"
      />
      <el-descriptions v-if="props.targetRecord" :column="2" border size="small">
        <el-descriptions-item label="来源序号">#{{ props.targetRecord.serial_no }}</el-descriptions-item>
        <el-descriptions-item label="客户">{{ props.targetRecord.customer_name }}</el-descriptions-item>
        <el-descriptions-item label="当前到期日">{{ props.targetRecord.due_month || "-" }}</el-descriptions-item>
        <el-descriptions-item label="当前总费用">{{ props.targetRecord.total_fee }}</el-descriptions-item>
      </el-descriptions>
      <BillingDraftRowsEditor
        :model-value="props.rows"
        title-prefix="续费明细"
        :allow-multiple="false"
        @update:model-value="emit('update:rows', $event)"
      />
    </el-space>
    <template #footer>
      <el-button @click="emit('update:visible', false)">取消</el-button>
      <el-button type="primary" :loading="props.loading" @click="emit('submit')">确认生成续费记录</el-button>
    </template>
  </el-dialog>
</template>
