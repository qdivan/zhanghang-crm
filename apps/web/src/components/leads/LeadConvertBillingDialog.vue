<script setup lang="ts">
import { computed } from "vue";

import BillingDraftRowsEditor from "../BillingDraftRowsEditor.vue";
import type { BillingCreatePayload } from "../../types";

const props = defineProps<{
  visible: boolean;
  customerName: string;
  rows: BillingCreatePayload[];
  loading: boolean;
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
  "update:rows": [value: BillingCreatePayload[]];
  submit: [];
}>();

const dialogVisible = computed({
  get: () => props.visible,
  set: (value: boolean) => emit("update:visible", value),
});

const rowsModel = computed({
  get: () => props.rows,
  set: (value: BillingCreatePayload[]) => emit("update:rows", value),
});

const dialogTitle = computed(() => `添加收费信息 - ${props.customerName}`);
</script>

<template>
  <el-dialog v-model="dialogVisible" :title="dialogTitle" width="760px">
    <el-form label-position="top">
      <el-form-item label="客户">
        <el-input :model-value="props.customerName" disabled />
      </el-form-item>
      <el-text type="info" size="small">
        同一客户可以连续增行多个收费项目，统一保存。常规新单只需填写收费类别、金额、服务开始日期、到期日期。
      </el-text>
    </el-form>
    <BillingDraftRowsEditor v-model="rowsModel" title-prefix="收费明细" />
    <template #footer>
      <el-button @click="dialogVisible = false">稍后添加</el-button>
      <el-button type="primary" :loading="props.loading" @click="emit('submit')">
        保存 {{ props.rows.length }} 条收费信息
      </el-button>
    </template>
  </el-dialog>
</template>
