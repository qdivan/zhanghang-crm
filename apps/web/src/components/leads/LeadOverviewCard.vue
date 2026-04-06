<script setup lang="ts">
import { MoreFilled } from "@element-plus/icons-vue";

import { useResponsive } from "../../composables/useResponsive";
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
  canDelete: boolean;
}>();

const emit = defineEmits<{
  company: [row: LeadItem];
  detail: [row: LeadItem];
  customer: [row: LeadItem];
  followup: [row: LeadItem];
  history: [row: LeadItem];
  convert: [row: LeadItem];
  revoke: [row: LeadItem];
  delete: [row: LeadItem];
}>();

const { isMobile } = useResponsive();

function mobileMetrics(row: LeadItem) {
  return [
    { label: "地区/国家", value: getLeadAreaText(row) || "-" },
    { label: "联络开始", value: getLeadStartText(row) || "-" },
    { label: "电话", value: row.phone || "-" },
    { label: "最后跟进", value: row.last_followup_date || row.last_feedback || "-" },
    { label: "提醒值", value: row.reminder_value || "-" },
  ].filter((item) => item.value !== "-");
}

function handleMobileCommand(command: string, row: LeadItem) {
  if (command === "detail") emit("detail", row);
  if (command === "followup") emit("followup", row);
  if (command === "history") emit("history", row);
  if (command === "customer") emit("customer", row);
  if (command === "convert") emit("convert", row);
  if (command === "revoke") emit("revoke", row);
  if (command === "delete") emit("delete", row);
}

function onMobileMenuCommand(command: { action: string; row: LeadItem }) {
  handleMobileCommand(command.action, command.row);
}
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="table-head">
        <span>客户开发</span>
        <el-tag type="success" effect="plain">{{ props.rows.length }} 条</el-tag>
      </div>
    </template>
    <div v-if="isMobile" v-loading="props.loading" class="mobile-record-list">
      <div v-for="row in props.rows" :key="row.id" class="mobile-record-card">
        <div class="mobile-record-head">
          <div class="mobile-record-main">
            <div class="mobile-lead-title">
              <el-button link type="primary" class="mobile-record-title" @click="emit('company', row)">
                {{ row.name }}
              </el-button>
              <el-tag size="small" effect="plain">{{ getTemplateLabel(row.template_type) }}</el-tag>
            </div>
            <div class="mobile-record-subtitle">
              {{ getLeadContactText(row) || "未填写联系人" }}
            </div>
          </div>
          <el-tag :type="statusTagType(row.status)" size="small">
            {{ getStatusLabel(row.status) }}
          </el-tag>
        </div>

        <div class="mobile-record-metrics">
          <div v-for="item in mobileMetrics(row)" :key="`${row.id}-${item.label}`" class="mobile-metric">
            <div class="mobile-metric-label">{{ item.label }}</div>
            <div class="mobile-metric-value">{{ item.value }}</div>
          </div>
        </div>

        <div v-if="row.main_business || row.reminder_value" class="mobile-record-note">
          <div v-if="row.main_business">主营/需求：{{ row.main_business }}</div>
          <div v-if="row.reminder_value">提醒值：{{ row.reminder_value }}</div>
        </div>

        <div class="mobile-actions">
          <el-button size="small" @click="emit('detail', row)">详情</el-button>
          <el-button size="small" type="primary" @click="emit('followup', row)">跟进</el-button>
          <el-button
            v-if="row.customer_id"
            size="small"
            type="success"
            plain
            @click="emit('customer', row)"
          >
            客户档案
          </el-button>
          <el-button
            v-else
            size="small"
            type="success"
            :disabled="!props.canConvert || row.status === 'CONVERTED'"
            @click="emit('convert', row)"
          >
            转化
          </el-button>
          <el-dropdown trigger="click" @command="onMobileMenuCommand">
            <el-button size="small" plain>
              更多
              <el-icon><MoreFilled /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item :command="{ action: 'history', row }">跟进历史</el-dropdown-item>
                <el-dropdown-item v-if="row.customer_id" :command="{ action: 'customer', row }">客户档案</el-dropdown-item>
                <el-dropdown-item
                  v-else
                  :command="{ action: 'convert', row }"
                  :disabled="!props.canConvert || row.status === 'CONVERTED'"
                >
                  转化成交
                </el-dropdown-item>
                <el-dropdown-item
                  v-if="row.status === 'CONVERTED'"
                  :command="{ action: 'revoke', row }"
                  :disabled="!props.canConvert"
                >
                  撤销转化
                </el-dropdown-item>
                <el-dropdown-item v-if="props.canDelete" :command="{ action: 'delete', row }">
                  删除线索
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </div>
    <el-table v-else v-loading="props.loading" :data="props.rows" stripe border>
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
        width="130"
        show-overflow-tooltip
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
            <el-button v-if="props.canDelete" link type="danger" @click="emit('delete', row)">删除</el-button>
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

.mobile-lead-title {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.mobile-actions :deep(.el-button) {
  margin-left: 0;
}
</style>
