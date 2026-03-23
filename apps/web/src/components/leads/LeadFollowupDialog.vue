<script setup lang="ts">
import { computed, watch } from "vue";

import FlexibleDateInput from "../shared/FlexibleDateInput.vue";
import type { LeadFollowupForm } from "../../views/lead/forms";
import {
  buildNextReminderDate,
  getDefaultReminderValueForGrade,
  leadGradeOptions,
  leadReminderOptions,
} from "../../views/lead/viewMeta";

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

watch(
  () => props.form.grade,
  (grade) => {
    const reminderValue = getDefaultReminderValueForGrade(grade);
    if (reminderValue) {
      props.form.reminder_value = reminderValue;
    }
  },
);

watch(
  [() => props.form.followup_at, () => props.form.reminder_value],
  ([followupAt, reminderValue]) => {
    props.form.next_reminder_at = buildNextReminderDate(followupAt, reminderValue);
  },
  { immediate: true },
);
</script>

<template>
  <el-dialog v-model="dialogVisible" title="新增开发跟进" width="720px">
    <el-form label-position="top">
      <el-row :gutter="12">
        <el-col :span="6">
          <el-form-item label="跟进日期">
            <FlexibleDateInput v-model="props.form.followup_at" :empty-value="''" />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="等级">
            <el-select v-model="props.form.grade">
              <el-option
                v-for="item in leadGradeOptions"
                :key="`followup-grade-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="提醒值">
            <el-select v-model="props.form.reminder_value">
              <el-option
                v-for="item in leadReminderOptions"
                :key="`followup-reminder-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="6">
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
