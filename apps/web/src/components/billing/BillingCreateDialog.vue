<script setup lang="ts">
import BillingDraftRowsEditor from "../BillingDraftRowsEditor.vue";
import type { BillingCreatePayload, CustomerListItem } from "../../types";

const props = defineProps<{
  visible: boolean;
  customerId: number | null;
  customers: CustomerListItem[];
  rows: BillingCreatePayload[];
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
  "update:customerId": [value: number | null];
  "update:rows": [value: BillingCreatePayload[]];
  submit: [];
}>();
</script>

<template>
  <el-dialog
    :model-value="props.visible"
    title="新增收费记录"
    width="760px"
    @update:model-value="emit('update:visible', $event)"
  >
    <el-form label-position="top">
      <el-form-item label="客户">
        <el-select
          :model-value="props.customerId"
          filterable
          placeholder="请选择客户"
          @update:model-value="emit('update:customerId', $event)"
        >
          <el-option
            v-for="item in props.customers"
            :key="item.id"
            :label="`${item.name}（${item.contact_name}）`"
            :value="item.id"
          />
        </el-select>
      </el-form-item>
      <el-text type="info" size="small">
        选择客户后，可连续增行多个收费项目并一次保存。按期项目填写开始月份即可默认生成 12 个月合同；按次项目再填写实际日期。
      </el-text>
    </el-form>

    <BillingDraftRowsEditor
      :model-value="props.rows"
      title-prefix="收费明细"
      @update:model-value="emit('update:rows', $event)"
    />

    <template #footer>
      <el-button @click="emit('update:visible', false)">取消</el-button>
      <el-button type="primary" @click="emit('submit')">保存 {{ props.rows.length }} 条</el-button>
    </template>
  </el-dialog>
</template>
