<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { apiClient } from "../api/client";
import { useResponsive } from "../composables/useResponsive";
import type { DashboardSummary, SystemTodoItem, TodoItem } from "../types";

const router = useRouter();
const { isMobile } = useResponsive();
const loading = ref(false);
const summary = ref<DashboardSummary>({
  month: "",
  lead_new_count: 0,
  lead_following_count: 0,
  customer_count: 0,
  billing_record_count: 0,
  outstanding_amount_total: 0,
  manual_open_todo_count: 0,
  system_todo_count: 0,
});
const systemTodos = ref<SystemTodoItem[]>([]);
const manualTodos = ref<TodoItem[]>([]);

const summaryItems = computed(() => [
  { label: "新线索", value: summary.value.lead_new_count },
  { label: "跟进中", value: summary.value.lead_following_count },
  { label: "客户总数", value: summary.value.customer_count },
  { label: "收费单", value: summary.value.billing_record_count },
  { label: "未收总额", value: summary.value.outstanding_amount_total, accent: true },
  { label: "手动待办", value: summary.value.manual_open_todo_count },
  { label: "系统待办", value: summary.value.system_todo_count },
]);

function priorityLabel(priority: string): string {
  if (priority === "HIGH") return "高";
  if (priority === "LOW") return "低";
  return "中";
}

function moduleLabel(module: SystemTodoItem["module"]): string {
  if (module === "LEAD") return "开发";
  if (module === "BILLING") return "收费";
  return "客户";
}

function hasSystemTodoAction(todo: SystemTodoItem): boolean {
  return Boolean((todo.action_path || "").trim() && (todo.action_label || "").trim());
}

function openSystemTodo(todo: SystemTodoItem) {
  const target = (todo.action_path || "").trim();
  if (!target) {
    ElMessage.warning("该待办未配置跳转地址");
    return;
  }
  router.push(target);
}

async function fetchDashboardData() {
  loading.value = true;
  try {
    const [summaryResp, systemResp, manualResp] = await Promise.all([
      apiClient.get<DashboardSummary>("/dashboard/summary"),
      apiClient.get<SystemTodoItem[]>("/dashboard/system-todos", { params: { limit: 10 } }),
      apiClient.get<TodoItem[]>("/todos", { params: { include_done: false, limit: 10 } }),
    ]);
    summary.value = summaryResp.data;
    systemTodos.value = systemResp.data;
    manualTodos.value = manualResp.data;
  } catch (error) {
    ElMessage.error("加载工作台失败");
  } finally {
    loading.value = false;
  }
}

onMounted(fetchDashboardData);
</script>

<template>
  <section class="dashboard-page" v-loading="loading">
    <header class="dashboard-head">
      <div>
        <div class="dashboard-title">工作台</div>
        <div class="dashboard-copy">{{ summary.month || "本月" }} 的开发、客户、收费和待办概览。</div>
      </div>
      <el-button size="small" @click="fetchDashboardData">刷新</el-button>
    </header>

    <section class="dashboard-summary" :class="{ mobile: isMobile }">
      <article
        v-for="item in summaryItems"
        :key="item.label"
        class="dashboard-stat"
        :class="{ accent: item.accent }"
      >
        <span class="dashboard-stat-label">{{ item.label }}</span>
        <strong class="dashboard-stat-value">{{ item.value }}</strong>
      </article>
    </section>

    <section class="dashboard-grid">
      <el-card shadow="never" class="dashboard-card">
        <template #header>
          <div class="table-head">
            <div>
              <div class="table-title">系统待办</div>
              <div class="table-copy">优先处理系统生成的提醒和跳转任务。</div>
            </div>
            <el-tag size="small" type="warning" effect="plain">{{ systemTodos.length }} 条</el-tag>
          </div>
        </template>
        <div v-if="isMobile" class="mobile-record-list">
          <div v-for="row in systemTodos" :key="row.id" class="mobile-record-card compact-mobile-card">
            <div class="mobile-record-head">
              <div class="mobile-record-main">
                <div class="mobile-record-title">{{ row.title }}</div>
                <div class="mobile-record-subtitle">{{ moduleLabel(row.module) }} · 截止 {{ row.due_date || "-" }}</div>
              </div>
              <el-tag size="small" :type="row.priority === 'HIGH' ? 'danger' : row.priority === 'LOW' ? 'info' : 'warning'">
                {{ priorityLabel(row.priority) }}
              </el-tag>
            </div>
            <div v-if="row.description" class="mobile-record-note">{{ row.description }}</div>
            <div v-if="hasSystemTodoAction(row)" class="mobile-actions compact-mobile-actions">
              <el-button size="small" type="primary" @click="openSystemTodo(row)">{{ row.action_label }}</el-button>
            </div>
          </div>
        </div>
        <el-table v-else :data="systemTodos" stripe border size="small" class="dashboard-table">
          <el-table-column label="模块" width="72">
            <template #default="{ row }">{{ moduleLabel(row.module) }}</template>
          </el-table-column>
          <el-table-column prop="title" label="任务" min-width="180" show-overflow-tooltip />
          <el-table-column label="优先级" width="78">
            <template #default="{ row }">
              <el-tag size="small" :type="row.priority === 'HIGH' ? 'danger' : row.priority === 'LOW' ? 'info' : 'warning'">
                {{ priorityLabel(row.priority) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="due_date" label="截止" width="110" />
          <el-table-column label="操作" width="96">
            <template #default="{ row }">
              <el-button v-if="hasSystemTodoAction(row)" link type="primary" @click="openSystemTodo(row)">
                {{ row.action_label }}
              </el-button>
              <span v-else>-</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card shadow="never" class="dashboard-card">
        <template #header>
          <div class="table-head">
            <div>
              <div class="table-title">手动待办</div>
              <div class="table-copy">个人补充的日常事项，和系统待办分开看。</div>
            </div>
            <el-tag size="small" type="success" effect="plain">{{ manualTodos.length }} 条</el-tag>
          </div>
        </template>
        <div v-if="isMobile" class="mobile-record-list">
          <div v-for="row in manualTodos" :key="row.id" class="mobile-record-card compact-mobile-card">
            <div class="mobile-record-head">
              <div class="mobile-record-main">
                <div class="mobile-record-title">{{ row.title }}</div>
                <div class="mobile-record-subtitle">截止 {{ row.due_date || "-" }}</div>
              </div>
              <el-tag size="small" :type="row.priority === 'HIGH' ? 'danger' : row.priority === 'LOW' ? 'info' : 'warning'">
                {{ priorityLabel(row.priority) }}
              </el-tag>
            </div>
          </div>
        </div>
        <el-table v-else :data="manualTodos" stripe border size="small" class="dashboard-table">
          <el-table-column prop="title" label="任务" min-width="180" show-overflow-tooltip />
          <el-table-column label="优先级" width="78">
            <template #default="{ row }">
              <el-tag size="small" :type="row.priority === 'HIGH' ? 'danger' : row.priority === 'LOW' ? 'info' : 'warning'">
                {{ priorityLabel(row.priority) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="due_date" label="截止" width="110" />
        </el-table>
      </el-card>
    </section>
  </section>
</template>

<style scoped>
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.dashboard-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 6px 2px 2px;
}

.dashboard-title {
  font-size: 18px;
  font-weight: 700;
  color: #172330;
}

.dashboard-copy {
  margin-top: 2px;
  font-size: 12px;
  color: #6b7280;
}

.dashboard-summary {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 10px;
}

.dashboard-summary.mobile {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.dashboard-stat {
  padding: 12px 14px;
  border: 1px solid #dfe6e8;
  background: #ffffff;
}

.dashboard-stat.accent {
  background: #f8fbfb;
}

.dashboard-stat-label {
  display: block;
  font-size: 12px;
  color: #6b7280;
}

.dashboard-stat-value {
  display: block;
  margin-top: 8px;
  font-size: 22px;
  line-height: 1;
  color: #172330;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.dashboard-card {
  border-color: #dfe6e8;
}

.table-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.table-title {
  font-size: 14px;
  font-weight: 700;
  color: #1f2937;
}

.table-copy {
  margin-top: 2px;
  font-size: 12px;
  line-height: 1.5;
  color: #6b7280;
}

.dashboard-table :deep(.el-table__cell) {
  padding: 8px 0;
}

.compact-mobile-card {
  padding: 10px 12px;
}

.compact-mobile-actions {
  margin-top: 10px;
}

@media (max-width: 1100px) {
  .dashboard-summary {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .dashboard-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .dashboard-summary.mobile {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
