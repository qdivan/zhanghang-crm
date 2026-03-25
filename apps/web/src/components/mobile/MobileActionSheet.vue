<script setup lang="ts">
type ActionSheetItem = {
  key: string;
  label: string;
  description?: string;
  danger?: boolean;
  disabled?: boolean;
};

withDefaults(
  defineProps<{
    modelValue: boolean;
    title: string;
    subtitle?: string;
    items: ActionSheetItem[];
    size?: string;
  }>(),
  {
    subtitle: "",
    size: "56vh",
  },
);

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
  select: [key: string];
}>();

function handleSelect(item: ActionSheetItem) {
  if (item.disabled) return;
  emit("select", item.key);
  emit("update:modelValue", false);
}
</script>

<template>
  <el-drawer
    :model-value="modelValue"
    direction="btt"
    :size="size"
    :with-header="false"
    class="mobile-action-sheet"
    @close="emit('update:modelValue', false)"
  >
    <div class="mobile-action-sheet-inner">
      <div class="mobile-action-sheet-handle"></div>
      <div class="mobile-action-sheet-head">
        <div>
          <div class="mobile-action-sheet-title">{{ title }}</div>
          <div v-if="subtitle" class="mobile-action-sheet-subtitle">{{ subtitle }}</div>
        </div>
        <el-button text @click="emit('update:modelValue', false)">关闭</el-button>
      </div>
      <div class="mobile-action-sheet-list">
        <button
          v-for="item in items"
          :key="item.key"
          type="button"
          class="mobile-action-sheet-item"
          :class="{ danger: item.danger, disabled: item.disabled }"
          :disabled="item.disabled"
          @click="handleSelect(item)"
        >
          <span class="mobile-action-sheet-item-label">{{ item.label }}</span>
          <span v-if="item.description" class="mobile-action-sheet-item-description">{{ item.description }}</span>
        </button>
      </div>
    </div>
  </el-drawer>
</template>

<style scoped>
.mobile-action-sheet-inner {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.mobile-action-sheet-handle {
  width: 44px;
  height: 4px;
  border-radius: 999px;
  background: #d5dde0;
  margin: 4px auto 10px;
}

.mobile-action-sheet-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.mobile-action-sheet-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.mobile-action-sheet-subtitle {
  margin-top: 3px;
  font-size: 12px;
  color: var(--app-text-muted);
}

.mobile-action-sheet-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 14px;
}

.mobile-action-sheet-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  width: 100%;
  padding: 14px;
  border: 1px solid var(--app-border-soft);
  border-radius: 16px;
  background: var(--app-surface);
  text-align: left;
}

.mobile-action-sheet-item-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--app-text-primary);
}

.mobile-action-sheet-item-description {
  font-size: 12px;
  line-height: 1.5;
  color: var(--app-text-muted);
}

.mobile-action-sheet-item.danger .mobile-action-sheet-item-label {
  color: #b42318;
}

.mobile-action-sheet-item.disabled {
  opacity: 0.52;
}

.mobile-action-sheet :deep(.el-drawer__body) {
  padding: 10px 16px max(16px, env(safe-area-inset-bottom));
  background: var(--app-surface);
}
</style>
