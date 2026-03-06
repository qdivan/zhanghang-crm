<script setup lang="ts">
import { ElMessage } from "element-plus";
import { onMounted, ref } from "vue";

import { apiClient } from "../api/client";
import type { DashboardSummary, SystemTodoItem, TodoItem } from "../types";

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

function priorityLabel(priority: string): string {
  if (priority === "HIGH") return "高";
  if (priority === "LOW") return "低";
  return "中";
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
  <el-space direction="vertical" fill :size="12" v-loading="loading">
    <el-card shadow="never">
      <div class="head">
        <div>
          <div class="title">工作台</div>
          <div class="subtitle">{{ summary.month || "本月" }} 任务概览</div>
        </div>
        <el-button @click="fetchDashboardData">刷新</el-button>
      </div>
    </el-card>

    <el-row :gutter="12">
      <el-col :xs="12" :md="6"><el-card shadow="never"><el-statistic title="新线索" :value="summary.lead_new_count" /></el-card></el-col>
      <el-col :xs="12" :md="6"><el-card shadow="never"><el-statistic title="跟进中" :value="summary.lead_following_count" /></el-card></el-col>
      <el-col :xs="12" :md="6"><el-card shadow="never"><el-statistic title="客户总数" :value="summary.customer_count" /></el-card></el-col>
      <el-col :xs="12" :md="6"><el-card shadow="never"><el-statistic title="收费记录" :value="summary.billing_record_count" /></el-card></el-col>
    </el-row>

    <el-row :gutter="12">
      <el-col :xs="24" :md="8"><el-card shadow="never"><el-statistic title="未收总额" :value="summary.outstanding_amount_total" /></el-card></el-col>
      <el-col :xs="12" :md="8"><el-card shadow="never"><el-statistic title="我的手动待办" :value="summary.manual_open_todo_count" /></el-card></el-col>
      <el-col :xs="12" :md="8"><el-card shadow="never"><el-statistic title="系统待办" :value="summary.system_todo_count" /></el-card></el-col>
    </el-row>

    <el-row :gutter="12">
      <el-col :xs="24" :lg="12">
        <el-card shadow="never">
          <template #header>
            <div class="table-head">
              <span>本月系统待办（前10）</span>
              <el-tag type="warning" effect="plain">{{ systemTodos.length }} 条</el-tag>
            </div>
          </template>
          <el-table :data="systemTodos" stripe border>
            <el-table-column prop="module" label="模块" width="80" />
            <el-table-column prop="title" label="任务" min-width="180" show-overflow-tooltip />
            <el-table-column label="优先级" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="row.priority === 'HIGH' ? 'danger' : row.priority === 'LOW' ? 'info' : 'warning'">
                  {{ priorityLabel(row.priority) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="due_date" label="截止" width="110" />
          </el-table>
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="12">
        <el-card shadow="never">
          <template #header>
            <div class="table-head">
              <span>我的手动待办（前10）</span>
              <el-tag type="success" effect="plain">{{ manualTodos.length }} 条</el-tag>
            </div>
          </template>
          <el-table :data="manualTodos" stripe border>
            <el-table-column prop="title" label="任务" min-width="180" show-overflow-tooltip />
            <el-table-column label="优先级" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="row.priority === 'HIGH' ? 'danger' : row.priority === 'LOW' ? 'info' : 'warning'">
                  {{ priorityLabel(row.priority) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="due_date" label="截止" width="110" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </el-space>
</template>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.title {
  font-size: 18px;
  font-weight: 600;
}

.subtitle {
  color: #6b7280;
  font-size: 12px;
  margin-top: 2px;
}

.table-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
