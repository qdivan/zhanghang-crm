<script setup lang="ts">
import { computed, ref } from "vue";

import { useResponsive } from "../../composables/useResponsive";
import type { LeadFilters } from "../../views/lead/forms";
import { statusOptions, templateOptions } from "../../views/lead/viewMeta";

const props = defineProps<{
  filters: LeadFilters;
  externalMode?: boolean;
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
  <el-card shadow="never" class="workspace-surface">
    <div class="workspace-inline-toolbar lead-toolbar">
      <div class="workspace-inline-toolbar-main">
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
          <el-form-item v-if="!props.externalMode" v-show="!isMobile || showAdvancedFilters" label="模板">
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
        </el-form>
      </div>
      <div class="workspace-inline-toolbar-actions action-group">
        <el-button size="small" @click="emit('query')">查询</el-button>
        <el-button size="small" type="primary" @click="emit('create')">新增线索</el-button>
        <el-button v-if="!props.externalMode" size="small" type="primary" plain @click="emit('redevelop')">老客二次开发</el-button>
        <el-button size="small" @click="emit('guide')">流程说明</el-button>
        <el-button v-if="!props.externalMode" size="small" @click="emit('importExcel')">导入 Excel</el-button>
      </div>
    </div>
    <div class="lead-toolbar-copy">
      {{
        props.externalMode
          ? "你只能查看和维护自己录入的线索。公司名保存时会自动加上你的项目前缀。"
          : "这里只显示未成单线索。默认按最新录入在前，可点表头按序号、名称或联络开始排序。"
      }}
    </div>
  </el-card>
</template>

<style scoped>
.lead-filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 10px;
}

.lead-filter-form :deep(.el-input),
.lead-filter-form :deep(.el-select) {
  min-width: 180px;
}

.action-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.lead-toolbar-copy {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--app-text-muted);
}

@media (max-width: 768px) {
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
