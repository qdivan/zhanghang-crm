<script setup lang="ts">
import { computed, ref } from "vue";

import { useResponsive } from "../../composables/useResponsive";
import type { LeadFilters } from "../../views/lead/forms";
import { statusOptions, templateOptions } from "../../views/lead/viewMeta";

const props = defineProps<{
  filters: LeadFilters;
}>();

const emit = defineEmits<{
  query: [];
  create: [];
  redevelop: [];
  guide: [];
  importExcel: [];
}>();

const { isMobile } = useResponsive();
const showAdvancedFilters = ref(false);
const hasAdvancedValue = computed(() => Boolean(props.filters.status || props.filters.template_type));
</script>

<template>
  <el-card shadow="never">
    <el-form inline @submit.prevent="emit('query')" class="lead-filter-form">
      <el-form-item label="关键词">
        <el-input
          v-model="props.filters.keyword"
          placeholder="客户/联系人/电话"
          clearable
          @keyup.enter="emit('query')"
        />
      </el-form-item>
      <el-form-item v-show="!isMobile || showAdvancedFilters" label="状态">
        <el-select v-model="props.filters.status" placeholder="全部" clearable>
          <el-option
            v-for="item in statusOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>
      <el-form-item v-show="!isMobile || showAdvancedFilters" label="模板筛选">
        <el-select v-model="props.filters.template_type" placeholder="全部" clearable>
          <el-option
            v-for="item in templateOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>
      <el-form-item v-if="isMobile">
        <el-button text @click="showAdvancedFilters = !showAdvancedFilters">
          {{ showAdvancedFilters ? "收起筛选" : hasAdvancedValue ? "更多筛选（已选）" : "更多筛选" }}
        </el-button>
      </el-form-item>
      <el-form-item>
        <div class="action-group">
          <el-button @click="emit('query')">查询</el-button>
          <el-button type="primary" @click="emit('create')">新增线索</el-button>
          <el-button type="primary" plain @click="emit('redevelop')">老客二次开发</el-button>
          <el-button @click="emit('guide')">流程说明</el-button>
          <el-button @click="emit('importExcel')">导入 Excel</el-button>
        </div>
      </el-form-item>
    </el-form>
    <el-text type="info">
      这里仅显示未成单线索；已成单客户统一进入“客户列表”。当前排序：跟进中（按下次提醒） -> 新线索 -> 已丢失
    </el-text>
  </el-card>
</template>

<style scoped>
.action-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

@media (max-width: 900px) {
  .lead-filter-form {
    display: flex;
    flex-wrap: wrap;
  }

  .action-group {
    display: grid;
    grid-template-columns: 1fr 1fr;
    width: 100%;
  }

  .action-group :deep(.el-button) {
    margin-left: 0;
  }
}
</style>
