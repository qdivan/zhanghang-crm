<script setup lang="ts">
import { computed } from "vue";

import { leadGuideStatusItems, leadGuideStepItems, leadGuideTemplateItems } from "../../views/lead/viewMeta";

const props = defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
}>();

const dialogVisible = computed({
  get: () => props.visible,
  set: (value: boolean) => emit("update:visible", value),
});
</script>

<template>
  <el-dialog v-model="dialogVisible" title="客户开发流程说明" width="760px">
    <el-space direction="vertical" fill :size="12">
      <el-card shadow="never">
        <template #header>状态说明</template>
        <el-descriptions :column="1" border>
          <el-descriptions-item
            v-for="item in leadGuideStatusItems"
            :key="`guide-status-${item.label}`"
            :label="item.label"
          >
            {{ item.value }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card shadow="never">
        <template #header>流程说明</template>
        <el-descriptions :column="1" border>
          <el-descriptions-item
            v-for="item in leadGuideStepItems"
            :key="`guide-step-${item.label}`"
            :label="item.label"
          >
            {{ item.value }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card shadow="never">
        <template #header>模板筛选说明</template>
        <el-descriptions :column="1" border>
          <el-descriptions-item
            v-for="item in leadGuideTemplateItems"
            :key="`guide-template-${item.label}`"
            :label="item.label"
          >
            {{ item.value }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>
    </el-space>
    <template #footer>
      <el-button type="primary" @click="dialogVisible = false">我知道了</el-button>
    </template>
  </el-dialog>
</template>
