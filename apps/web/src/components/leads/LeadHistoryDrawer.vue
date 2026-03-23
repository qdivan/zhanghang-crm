<script setup lang="ts">
import { computed } from "vue";

import { useResponsive } from "../../composables/useResponsive";

type FollowupItem = {
  id: number;
  lead_id: number;
  followup_at: string;
  feedback: string;
  next_reminder_at: string | null;
  notes: string;
  created_by: number;
  created_by_username: string;
  created_at: string;
};

const props = defineProps<{
  visible: boolean;
  leadName: string;
  loading: boolean;
  rows: FollowupItem[];
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
}>();

const drawerVisible = computed({
  get: () => props.visible,
  set: (value: boolean) => emit("update:visible", value),
});

const drawerTitle = computed(() => `开发跟进历史 - ${props.leadName}`);
const { isMobile } = useResponsive();
</script>

<template>
  <el-drawer v-model="drawerVisible" :title="drawerTitle" size="min(760px, 92vw)">
    <div v-if="isMobile" v-loading="props.loading" class="mobile-record-list">
      <div v-for="row in props.rows" :key="row.id" class="mobile-record-card">
        <div class="mobile-record-head">
          <div class="mobile-record-main">
            <div class="mobile-record-title">{{ row.followup_at }}</div>
            <div class="mobile-record-subtitle">
              记录人：{{ row.created_by_username || "-" }} · 下次提醒：{{ row.next_reminder_at || "-" }}
            </div>
          </div>
        </div>
        <div class="detail-long-fields">
          <div class="detail-long-field">
            <div class="detail-long-label">跟进反馈</div>
            <div class="detail-long-value">{{ row.feedback || "-" }}</div>
          </div>
          <div class="detail-long-field">
            <div class="detail-long-label">备注</div>
            <div class="detail-long-value">{{ row.notes || "-" }}</div>
          </div>
        </div>
      </div>
    </div>
    <el-table v-else v-loading="props.loading" :data="props.rows" stripe border>
      <el-table-column prop="followup_at" label="跟进日期" width="120" />
      <el-table-column prop="feedback" label="跟进反馈" min-width="180" show-overflow-tooltip />
      <el-table-column
        prop="next_reminder_at"
        label="下次提醒"
        width="120"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        prop="notes"
        label="备注"
        min-width="130"
        show-overflow-tooltip
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column prop="created_by_username" label="记录人" width="100" />
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
