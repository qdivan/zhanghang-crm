<script setup lang="ts">
import { computed } from "vue";

import FlexibleDateInput from "../shared/FlexibleDateInput.vue";
import type { LeadFollowupForm } from "../../views/lead/forms";

const props = defineProps<{
  visible: boolean;
  form: LeadFollowupForm;
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
  submit: [];
}>();

const dialogVisible = computed({
  get: () => props.visible,
  set: (value: boolean) => emit("update:visible", value),
});
</script>

<template>
  <el-dialog v-model="dialogVisible" title="新增跟进" width="520px">
    <el-form label-position="top">
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="跟进日期">
            <FlexibleDateInput v-model="props.form.followup_at" :empty-value="''" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="下次提醒">
            <FlexibleDateInput v-model="props.form.next_reminder_at" clearable />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="跟进反馈">
        <el-input v-model="props.form.feedback" type="textarea" :rows="3" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="props.form.notes" type="textarea" :rows="2" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="emit('submit')">保存</el-button>
    </template>
  </el-dialog>
</template>
