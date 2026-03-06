<script setup lang="ts">
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
      <el-form-item label="状态">
        <el-select v-model="props.filters.status" placeholder="全部" clearable>
          <el-option
            v-for="item in statusOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="模板筛选">
        <el-select v-model="props.filters.template_type" placeholder="全部" clearable>
          <el-option
            v-for="item in templateOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button @click="emit('query')">查询</el-button>
        <el-button type="primary" @click="emit('create')">新增线索</el-button>
        <el-button type="primary" plain @click="emit('redevelop')">老客二次开发</el-button>
        <el-button @click="emit('guide')">流程说明</el-button>
        <el-button @click="emit('importExcel')">导入 Excel</el-button>
      </el-form-item>
    </el-form>
    <el-text type="info">
      当前排序：跟进中（按下次提醒） -> 新线索 -> 已丢失 -> 已转化（置底）
    </el-text>
  </el-card>
</template>

<style scoped>
@media (max-width: 900px) {
  .lead-filter-form {
    display: flex;
    flex-wrap: wrap;
  }
}
</style>
