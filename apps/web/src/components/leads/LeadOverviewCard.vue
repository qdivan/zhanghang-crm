<script setup lang="ts">
import type { LeadItem } from "../../types";
import {
  getLeadAreaText,
  getLeadContactText,
  getLeadStartText,
  getStatusLabel,
  getTemplateLabel,
  statusTagType,
} from "../../views/lead/viewMeta";

const props = defineProps<{
  loading: boolean;
  rows: LeadItem[];
  canConvert: boolean;
}>();

const emit = defineEmits<{
  company: [row: LeadItem];
  detail: [row: LeadItem];
  customer: [row: LeadItem];
  followup: [row: LeadItem];
  history: [row: LeadItem];
  convert: [row: LeadItem];
  revoke: [row: LeadItem];
}>();
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="table-head">
        <span>客户开发总览（对齐 `转化2026 > 客户总览`）</span>
        <el-tag type="success" effect="plain">{{ props.rows.length }} 条</el-tag>
      </div>
    </template>
    <el-table v-loading="props.loading" :data="props.rows" stripe border>
      <el-table-column prop="id" label="序号" width="70" />
      <el-table-column label="公司名" min-width="150" show-overflow-tooltip>
        <template #default="{ row }">
          <div class="lead-name-cell">
            <el-button link type="primary" @click="emit('company', row)">
              {{ row.name }}
            </el-button>
            <el-tag size="small" effect="plain">{{ getTemplateLabel(row.template_type) }}</el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column
        prop="grade"
        label="等级"
        width="70"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        label="地区/国家"
        width="110"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      >
        <template #default="{ row }">{{ getLeadAreaText(row) }}</template>
      </el-table-column>
      <el-table-column
        label="联络/服务开始"
        width="120"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      >
        <template #default="{ row }">{{ getLeadStartText(row) }}</template>
      </el-table-column>
      <el-table-column
        label="联系人（微信号）"
        min-width="160"
        show-overflow-tooltip
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      >
        <template #default="{ row }">{{ getLeadContactText(row) }}</template>
      </el-table-column>
      <el-table-column
        prop="main_business"
        label="主营/需求"
        min-width="180"
        show-overflow-tooltip
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        prop="phone"
        label="电话"
        width="130"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        label="状态"
        width="100"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      >
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">
            {{ getStatusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column
        prop="last_followup_date"
        label="最后跟进日期"
        width="120"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        prop="reminder_value"
        label="提醒值"
        width="90"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        label="操作"
        width="250"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      >
        <template #default="{ row }">
          <el-space class="table-action-wrap">
            <el-button link @click="emit('detail', row)">详情</el-button>
            <el-button v-if="row.customer_id" link type="primary" @click="emit('customer', row)">
              客户档案
            </el-button>
            <el-button link type="primary" @click="emit('followup', row)">跟进</el-button>
            <el-button link @click="emit('history', row)">历史</el-button>
            <el-button
              link
              type="success"
              :disabled="!props.canConvert || row.status === 'CONVERTED'"
              @click="emit('convert', row)"
            >
              转化
            </el-button>
            <el-button
              v-if="row.status === 'CONVERTED'"
              link
              type="danger"
              :disabled="!props.canConvert"
              @click="emit('revoke', row)"
            >
              撤销转化
            </el-button>
          </el-space>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<style scoped>
.table-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.lead-name-cell {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
