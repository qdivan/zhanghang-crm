<script setup lang="ts">
import { MoreFilled } from "@element-plus/icons-vue";
import { todayInBrowserTimeZone } from "../../utils/time";

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
  sortProp: string;
  sortOrder: "ascending" | "descending" | null;
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
  "sort-change": [payload: { prop: string | undefined; order: "ascending" | "descending" | null; columnKey?: string }];
}>();

const { isMobile } = useResponsive();
const todayText = todayInBrowserTimeZone();

function reminderDay(value: string | null) {
  return value ? value.slice(0, 10) : "";
}

function followupFlagLevel(row: LeadItem): "OVERDUE" | "TODAY" | "NONE" {
  if (row.status === "CONVERTED" || row.status === "LOST") return "NONE";
  const reminder = reminderDay(row.next_reminder_at);
  if (!reminder) return "NONE";
  if (reminder < todayText) return "OVERDUE";
  if (reminder === todayText) return "TODAY";
  return "NONE";
}

function followupFlagLabel(row: LeadItem) {
  const level = followupFlagLevel(row);
  if (level === "OVERDUE") return "超期未跟进";
  if (level === "TODAY") return "今日需跟进";
  return "";
}

function desktopRowClassName({ row }: { row: LeadItem }) {
  const level = followupFlagLevel(row);
  if (level === "OVERDUE") return "lead-row-overdue";
  if (level === "TODAY") return "lead-row-today";
  return "";
}

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
      <div class="table-head workspace-section-head">
        <div>
          <div class="workspace-section-title">客户开发</div>
          <div class="workspace-section-copy">默认按最新录入在前，超期未跟进会在列表里重点标出。</div>
        </div>
        <el-tag type="success" effect="plain" class="workspace-subtle-tag">{{ props.rows.length }} 条</el-tag>
      </div>
    </template>
    <div v-if="isMobile" v-loading="props.loading" class="mobile-record-list">
      <div
        v-for="row in props.rows"
        :key="row.id"
        class="mobile-record-card"
        :class="{
          'lead-mobile-card-overdue': followupFlagLevel(row) === 'OVERDUE',
          'lead-mobile-card-today': followupFlagLevel(row) === 'TODAY',
        }"
      >
        <div class="mobile-record-head">
          <div class="mobile-record-main">
            <div class="mobile-lead-title">
              <el-button link type="primary" class="mobile-record-title" @click="emit('company', row)">
                {{ row.name }}
              </el-button>
              <el-tag size="small" effect="plain">{{ getTemplateLabel(row.template_type) }}</el-tag>
              <el-tag v-if="followupFlagLabel(row)" size="small" :type="followupFlagLevel(row) === 'OVERDUE' ? 'danger' : 'warning'" effect="dark">
                {{ followupFlagLabel(row) }}
              </el-tag>
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
          <el-popconfirm
            v-if="props.canDelete"
            title="确认删除这条线索吗？"
            confirm-button-text="删除"
            cancel-button-text="取消"
            @confirm="emit('delete', row)"
          >
            <template #reference>
              <el-button size="small" type="danger" plain>删除</el-button>
            </template>
          </el-popconfirm>
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
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </div>
    <el-table
      v-else
      v-loading="props.loading"
      :data="props.rows"
      stripe
      border
      size="small"
      class="lead-desktop-table workspace-table-compact"
      :default-sort="{ prop: props.sortProp, order: props.sortOrder }"
      :row-class-name="desktopRowClassName"
      @sort-change="emit('sort-change', $event)"
    >
      <el-table-column prop="id" label="序号" width="70" sortable="custom" />
      <el-table-column label="公司名" min-width="140" show-overflow-tooltip column-key="name" sortable="custom">
        <template #default="{ row }">
          <div class="lead-name-cell">
            <el-button link type="primary" @click="emit('company', row)">
              {{ row.name }}
            </el-button>
            <el-tag size="small" effect="plain">{{ getTemplateLabel(row.template_type) }}</el-tag>
            <el-tag
              v-if="followupFlagLabel(row)"
              size="small"
              :type="followupFlagLevel(row) === 'OVERDUE' ? 'danger' : 'warning'"
              effect="dark"
              class="lead-followup-flag"
            >
              {{ followupFlagLabel(row) }}
            </el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column
        prop="grade"
        label="等级"
        width="106"
        show-overflow-tooltip
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        label="地区/国家"
        width="96"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      >
        <template #default="{ row }">{{ getLeadAreaText(row) }}</template>
      </el-table-column>
      <el-table-column
        label="联络/服务开始"
        width="112"
        column-key="contact_start_date"
        sortable="custom"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      >
        <template #default="{ row }">{{ getLeadStartText(row) }}</template>
      </el-table-column>
      <el-table-column
        label="联系人（微信号）"
        min-width="148"
        column-key="contact_name"
        sortable="custom"
        show-overflow-tooltip
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      >
        <template #default="{ row }">{{ getLeadContactText(row) }}</template>
      </el-table-column>
      <el-table-column
        prop="main_business"
        label="主营/需求"
        min-width="160"
        show-overflow-tooltip
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        prop="phone"
        label="电话"
        width="118"
        sortable="custom"
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
        width="112"
        sortable="custom"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        prop="reminder_value"
        label="提醒值"
        width="84"
        class-name="mobile-hide"
        label-class-name="mobile-hide"
      />
      <el-table-column
        label="操作"
        width="220"
        fixed="right"
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
            <el-popconfirm
              v-if="props.canDelete"
              title="确认删除这条线索吗？"
              confirm-button-text="删除"
              cancel-button-text="取消"
              @confirm="emit('delete', row)"
            >
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </el-space>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<style scoped>
.lead-name-cell {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px 8px;
}

.lead-desktop-table :deep(.el-table__cell) {
  padding: 6px 0;
}

.lead-desktop-table :deep(.lead-row-overdue td.el-table__cell) {
  background: linear-gradient(90deg, rgba(201, 87, 58, 0.14), rgba(255, 248, 244, 0.9) 34%, #ffffff 80%);
}

.lead-desktop-table :deep(.lead-row-overdue td.el-table__cell:first-child .cell) {
  box-shadow: inset 3px 0 0 rgba(201, 87, 58, 0.88);
}

.lead-desktop-table :deep(.lead-row-today td.el-table__cell) {
  background: linear-gradient(90deg, rgba(217, 164, 57, 0.12), rgba(255, 251, 241, 0.88) 34%, #ffffff 80%);
}

.lead-desktop-table :deep(.lead-row-today td.el-table__cell:first-child .cell) {
  box-shadow: inset 3px 0 0 rgba(217, 164, 57, 0.84);
}

.table-action-wrap {
  flex-wrap: wrap;
  row-gap: 2px;
}

.lead-followup-flag {
  letter-spacing: 0.01em;
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

.lead-mobile-card-overdue {
  border-color: rgba(201, 87, 58, 0.28);
  background: linear-gradient(180deg, rgba(255, 247, 242, 0.96), #ffffff 64%);
  box-shadow: 0 10px 24px rgba(201, 87, 58, 0.08);
}

.lead-mobile-card-today {
  border-color: rgba(217, 164, 57, 0.28);
  background: linear-gradient(180deg, rgba(255, 251, 240, 0.96), #ffffff 64%);
}
</style>
