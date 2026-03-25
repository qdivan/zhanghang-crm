<script setup lang="ts">
withDefaults(
  defineProps<{
    modelValue: boolean;
    title: string;
    size?: string;
    subtitle?: string;
    summaryItems?: string[];
    emptySummary?: string;
  }>(),
  {
    size: "78vh",
    subtitle: "",
    summaryItems: () => [],
    emptySummary: "",
  },
);

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
}>();
</script>

<template>
  <el-drawer
    :model-value="modelValue"
    direction="btt"
    :size="size"
    :with-header="false"
    class="mobile-filter-sheet"
    @close="emit('update:modelValue', false)"
  >
    <div class="mobile-filter-sheet-inner">
      <div class="mobile-filter-sheet-handle"></div>
      <div class="mobile-filter-sheet-head">
        <div>
          <div class="mobile-filter-sheet-title">{{ title }}</div>
          <div v-if="subtitle" class="mobile-filter-sheet-subtitle">{{ subtitle }}</div>
        </div>
        <el-button text @click="emit('update:modelValue', false)">关闭</el-button>
      </div>
      <div v-if="summaryItems.length || emptySummary" class="mobile-filter-sheet-summary">
        <div v-if="summaryItems.length" class="mobile-filter-sheet-pills">
          <span v-for="item in summaryItems" :key="item" class="mobile-filter-sheet-pill">{{ item }}</span>
        </div>
        <div v-else class="mobile-filter-sheet-summary-copy">{{ emptySummary }}</div>
      </div>
      <div class="mobile-filter-sheet-body">
        <slot />
      </div>
      <div v-if="$slots.footer" class="mobile-filter-sheet-footer">
        <slot name="footer" />
      </div>
    </div>
  </el-drawer>
</template>

<style scoped>
.mobile-filter-sheet-inner {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.mobile-filter-sheet-handle {
  width: 44px;
  height: 4px;
  border-radius: 999px;
  background: #d5dde0;
  margin: 4px auto 10px;
}

.mobile-filter-sheet-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.mobile-filter-sheet-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.mobile-filter-sheet-subtitle {
  margin-top: 3px;
  font-size: 12px;
  color: var(--app-text-muted);
}

.mobile-filter-sheet-summary {
  margin-top: 12px;
  padding: 10px 0 12px;
  border-top: 1px solid var(--app-border-soft);
  border-bottom: 1px solid var(--app-border-soft);
}

.mobile-filter-sheet-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.mobile-filter-sheet-pill {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  background: var(--app-bg-soft);
  font-size: 12px;
  color: var(--app-text-secondary);
}

.mobile-filter-sheet-summary-copy {
  font-size: 12px;
  color: var(--app-text-muted);
}

.mobile-filter-sheet-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 12px 0;
}

.mobile-filter-sheet-footer {
  display: flex;
  gap: 10px;
  padding-top: 12px;
  border-top: 1px solid var(--app-border-soft);
}

.mobile-filter-sheet-footer :deep(.el-button) {
  flex: 1;
  min-width: 0;
}

.mobile-filter-sheet :deep(.el-drawer__body) {
  padding: 10px 16px max(16px, env(safe-area-inset-bottom));
  background: var(--app-surface);
}
</style>
