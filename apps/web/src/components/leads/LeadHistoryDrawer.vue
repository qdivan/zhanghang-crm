<script setup lang="ts">
import { computed } from "vue";

type FollowupItem = {
  id: number;
  lead_id: number;
  followup_at: string;
  feedback: string;
  next_reminder_at: string | null;
  notes: string;
  created_by: number;
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

const drawerTitle = computed(() => `跟进历史 - ${props.leadName}`);
</script>

<template>
  <el-drawer v-model="drawerVisible" :title="drawerTitle" size="min(760px, 92vw)">
    <el-table v-loading="props.loading" :data="props.rows" stripe border>
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
    </el-table>
  </el-drawer>
</template>
