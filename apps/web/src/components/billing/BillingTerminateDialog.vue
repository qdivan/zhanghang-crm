<script setup lang="ts">
import { computed } from "vue";

import FlexibleDateInput from "../shared/FlexibleDateInput.vue";
import type { BillingRecord } from "../../types";
import type { BillingTerminateForm } from "../../views/billing/forms";

const props = defineProps<{
  visible: boolean;
  targetRecord: BillingRecord | null;
  form: BillingTerminateForm;
  submitting: boolean;
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
  submit: [];
}>();

const dialogVisible = computed({
  get: () => props.visible,
  set: (value: boolean) => emit("update:visible", value),
});

const dialogTitle = computed(() => `提前终止合同 - ${props.targetRecord?.customer_name ?? ""}`);
</script>

<template>
  <el-dialog v-model="dialogVisible" :title="dialogTitle" width="560px">
    <el-form label-position="top">
      <el-form-item label="终止日期">
        <FlexibleDateInput v-model="props.form.terminated_at" />
      </el-form-item>
      <el-form-item label="冲减费用">
        <el-input-number v-model="props.form.reduced_fee" :min="0" :controls="false" style="width:100%" />
      </el-form-item>
      <el-form-item label="终止原因">
        <el-input v-model="props.form.reason" type="textarea" :rows="3" />
      </el-form-item>
      <el-text type="info" size="small">提交后会更新该收费单的应收总额、到期日和账单状态。</el-text>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="danger" :loading="props.submitting" @click="emit('submit')">确认终止并冲减</el-button>
    </template>
  </el-dialog>
</template>
