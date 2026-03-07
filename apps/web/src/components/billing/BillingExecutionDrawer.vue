<script setup lang="ts">
import { computed } from "vue";

import { useResponsive } from "../../composables/useResponsive";
import FlexibleDateInput from "../shared/FlexibleDateInput.vue";
import type { BillingExecutionLogItem, BillingRecord } from "../../types";
import type { BillingExecutionForm } from "../../views/billing/forms";
import { progressTypeLabel, progressTypeOptions, progressTypeTagType } from "../../views/billing/viewMeta";

const props = defineProps<{
  visible: boolean;
  targetRecord: BillingRecord | null;
  form: BillingExecutionForm;
  submitting: boolean;
  loading: boolean;
  rows: BillingExecutionLogItem[];
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
  submit: [];
}>();

const drawerVisible = computed({
  get: () => props.visible,
  set: (value: boolean) => emit("update:visible", value),
});

const drawerTitle = computed(() => `执行进度 - ${props.targetRecord?.customer_name ?? ""}`);
const { isMobile } = useResponsive();
</script>

<template>
  <el-drawer v-model="drawerVisible" :title="drawerTitle" size="min(760px, 92vw)">
    <el-form label-position="top">
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="进度类型">
            <el-select v-model="props.form.progress_type">
              <el-option
                v-for="item in progressTypeOptions"
                :key="`progress-type-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="进度日期">
            <FlexibleDateInput v-model="props.form.occurred_at" :empty-value="''" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="目标完成日">
            <FlexibleDateInput v-model="props.form.due_date" clearable />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="进度内容">
        <el-input v-model="props.form.content" type="textarea" :rows="3" />
      </el-form-item>
      <el-form-item label="下一步动作">
        <el-input v-model="props.form.next_action" placeholder="例如：等待客户回传材料、预约办理时间" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="props.form.note" />
      </el-form-item>
      <el-button type="primary" :loading="props.submitting" @click="emit('submit')">保存进度</el-button>
    </el-form>

    <el-divider />

    <div v-if="isMobile" v-loading="props.loading" class="mobile-record-list">
      <div v-for="row in props.rows" :key="row.id" class="mobile-record-card">
        <div class="mobile-record-head">
          <div class="mobile-record-main">
            <div class="mobile-record-title">{{ row.occurred_at }}</div>
            <div class="mobile-record-subtitle">
              {{ progressTypeLabel(row.progress_type) }} · 目标 {{ row.due_date || "-" }}
            </div>
          </div>
        </div>
        <div class="detail-long-fields">
          <div class="detail-long-field">
            <div class="detail-long-label">进度内容</div>
            <div class="detail-long-value">{{ row.content || "-" }}</div>
          </div>
          <div class="detail-long-field">
            <div class="detail-long-label">下一步</div>
            <div class="detail-long-value">{{ row.next_action || "-" }}</div>
          </div>
          <div class="detail-long-field">
            <div class="detail-long-label">备注</div>
            <div class="detail-long-value">{{ row.note || "-" }}</div>
          </div>
        </div>
      </div>
    </div>
    <el-table v-else v-loading="props.loading" :data="props.rows" stripe border>
      <el-table-column prop="occurred_at" label="日期" width="110" />
      <el-table-column label="类型" width="100">
        <template #default="{ row }">
          <el-tag :type="progressTypeTagType(row.progress_type)" size="small">
            {{ progressTypeLabel(row.progress_type) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="content" label="进度内容" min-width="220" show-overflow-tooltip />
      <el-table-column prop="next_action" label="下一步" min-width="180" show-overflow-tooltip />
      <el-table-column prop="due_date" label="目标完成" width="110" />
      <el-table-column prop="actor_username" label="记录人" width="100" />
      <el-table-column prop="note" label="备注" min-width="130" show-overflow-tooltip />
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
