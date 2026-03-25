<script setup lang="ts">
import { Delete } from "@element-plus/icons-vue";
import { computed, onMounted, ref, watch } from "vue";

import {
  formatTodoDate,
  priorityLabel,
  priorityTagType,
  useTodoWorkspace,
} from "../composables/useTodoWorkspace";
import { useResponsive } from "../composables/useResponsive";

const {
  activeTab,
  loading,
  creating,
  actionLoadingTodoId,
  allRows,
  todayRows,
  systemRows,
  createForm,
  openManualCount,
  refreshAll,
  createTodo,
  toggleTodoDone,
  toggleTodayMembership,
  addAllToToday,
  clearToday,
  removeTodo,
  openSystemAction,
} = useTodoWorkspace();

const { isMobile } = useResponsive();
const mobileDrawerVisible = ref(false);
const desktopPanelOpen = ref(false);

const desktopButtonText = computed(() => {
  if (desktopPanelOpen.value) return "收起 Todo";
  return `Todo ${todayRows.value.length}/${openManualCount.value}`;
});

async function handleSystemAction(row: typeof systemRows.value[number]) {
  await openSystemAction(row);
  mobileDrawerVisible.value = false;
  desktopPanelOpen.value = false;
}

function toggleDesktopPanel() {
  desktopPanelOpen.value = !desktopPanelOpen.value;
}

onMounted(() => {
  void refreshAll();
});

watch(isMobile, (value) => {
  if (!value) {
    mobileDrawerVisible.value = false;
  }
});
</script>

<template>
  <template v-if="!isMobile">
    <el-button class="todo-toggle-btn" type="primary" @click="toggleDesktopPanel">
      {{ desktopButtonText }}
    </el-button>

    <transition name="todo-slide">
      <div v-show="desktopPanelOpen" class="todo-desktop-panel" v-loading="loading">
        <el-card shadow="always">
          <template #header>
            <div class="head">
              <span>Todo</span>
              <el-space>
                <el-tag type="success" effect="plain">今日 {{ todayRows.length }}</el-tag>
                <el-tag type="warning" effect="plain">系统 {{ systemRows.length }}</el-tag>
                <el-button link type="primary" @click="refreshAll">刷新</el-button>
              </el-space>
            </div>
          </template>

          <div class="todo-panel-body">
            <el-tabs v-model="activeTab" class="todo-tabs">
              <el-tab-pane label="今日任务" name="today">
                <div class="todo-scroll">
                  <el-empty v-if="todayRows.length === 0" description="今日任务为空（未完成任务会留在“全部任务”）" />
                  <el-space v-else direction="vertical" fill :size="8" class="todo-list-wrap">
                    <div v-for="row in todayRows" :key="`today-${row.id}`" class="todo-row">
                      <div class="todo-main">
                        <div class="todo-title-line">
                          <el-checkbox
                            :model-value="row.status === 'DONE'"
                            :disabled="actionLoadingTodoId === row.id"
                            @change="(checked: unknown) => toggleTodoDone(row, Boolean(checked))"
                          />
                          <span class="todo-title">{{ row.title }}</span>
                        </div>
                        <div class="todo-meta">
                          <el-tag :type="priorityTagType(row.priority)" size="small">{{ priorityLabel(row.priority) }}</el-tag>
                          <span>截止 {{ formatTodoDate(row.due_date) }}</span>
                        </div>
                      </div>
                      <el-space :size="4">
                        <el-button
                          link
                          type="warning"
                          :loading="actionLoadingTodoId === row.id"
                          @click="toggleTodayMembership(row, false)"
                        >
                          撤销今日
                        </el-button>
                        <el-button
                          link
                          type="danger"
                          :icon="Delete"
                          :loading="actionLoadingTodoId === row.id"
                          @click="removeTodo(row)"
                        >
                          删除
                        </el-button>
                      </el-space>
                    </div>
                  </el-space>
                </div>
              </el-tab-pane>

              <el-tab-pane label="全部任务" name="all">
                <div class="todo-scroll">
                  <el-space class="bulk-actions" wrap>
                    <el-button type="primary" plain size="small" @click="addAllToToday">全部加入今日</el-button>
                    <el-button type="warning" plain size="small" @click="clearToday">撤销今日列表</el-button>
                  </el-space>

                  <el-space direction="vertical" fill :size="8" class="todo-list-wrap">
                    <div v-for="row in allRows" :key="`all-${row.id}`" class="todo-row" :class="{ done: row.status === 'DONE' }">
                      <div class="todo-main">
                        <div class="todo-title-line">
                          <el-checkbox
                            :model-value="row.status === 'DONE'"
                            :disabled="actionLoadingTodoId === row.id"
                            @change="(checked: unknown) => toggleTodoDone(row, Boolean(checked))"
                          />
                          <span class="todo-title">{{ row.title }}</span>
                          <el-tag v-if="row.is_in_today && row.status === 'OPEN'" type="success" size="small">今日</el-tag>
                        </div>
                        <div class="todo-meta">
                          <el-tag :type="priorityTagType(row.priority)" size="small">{{ priorityLabel(row.priority) }}</el-tag>
                          <span>截止 {{ formatTodoDate(row.due_date) }}</span>
                          <span>状态 {{ row.status === "DONE" ? "已完成" : "未完成" }}</span>
                        </div>
                      </div>
                      <el-space :size="4">
                        <el-button
                          v-if="row.status === 'OPEN'"
                          link
                          :type="row.is_in_today ? 'warning' : 'primary'"
                          :loading="actionLoadingTodoId === row.id"
                          @click="toggleTodayMembership(row, !row.is_in_today)"
                        >
                          {{ row.is_in_today ? "撤销今日" : "加入今日" }}
                        </el-button>
                        <el-button
                          link
                          type="danger"
                          :icon="Delete"
                          :loading="actionLoadingTodoId === row.id"
                          @click="removeTodo(row)"
                        >
                          删除
                        </el-button>
                      </el-space>
                    </div>
                  </el-space>
                </div>
              </el-tab-pane>

              <el-tab-pane label="系统待办" name="system">
                <div class="todo-scroll">
                  <el-empty v-if="systemRows.length === 0" description="暂无系统待办" />
                  <el-space v-else direction="vertical" fill :size="8" class="todo-list-wrap">
                    <div v-for="item in systemRows" :key="item.id" class="todo-row system-row">
                      <div class="todo-main">
                        <div class="todo-title-line">
                          <el-tag size="small" :type="item.module === 'BILLING' ? 'warning' : 'info'">
                            {{ item.module === "BILLING" ? "收款" : "线索" }}
                          </el-tag>
                          <span class="todo-title">{{ item.title }}</span>
                        </div>
                        <div class="todo-meta">
                          <el-tag :type="priorityTagType(item.priority)" size="small">{{ priorityLabel(item.priority) }}</el-tag>
                          <span>截止 {{ formatTodoDate(item.due_date) }}</span>
                          <span>负责人 {{ item.assignee_username || '-' }}</span>
                        </div>
                      </div>
                      <el-button link type="primary" @click="handleSystemAction(item)">{{ item.action_label }}</el-button>
                    </div>
                  </el-space>
                </div>
              </el-tab-pane>
            </el-tabs>

            <div class="todo-footer">
              <el-form inline @submit.prevent="createTodo" class="todo-create-form">
                <el-form-item>
                  <el-input
                    v-model="createForm.title"
                    :placeholder="activeTab === 'today' ? '添加到今日任务' : '添加新任务'"
                    clearable
                    @keyup.enter="createTodo"
                  />
                </el-form-item>
                <el-form-item>
                  <el-date-picker v-model="createForm.due_date" type="date" value-format="YYYY-MM-DD" placeholder="截止日" />
                </el-form-item>
                <el-form-item>
                  <el-select v-model="createForm.priority" placeholder="优先级">
                    <el-option label="高" value="HIGH" />
                    <el-option label="中" value="MEDIUM" />
                    <el-option label="低" value="LOW" />
                  </el-select>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :loading="creating" @click="createTodo">添加</el-button>
                </el-form-item>
              </el-form>
            </div>
          </div>
        </el-card>
      </div>
    </transition>
  </template>

  <el-button v-else class="todo-fab" type="primary" circle @click="mobileDrawerVisible = true">T</el-button>
  <el-drawer v-model="mobileDrawerVisible" title="Todo" direction="rtl" size="92vw" @opened="refreshAll">
    <div class="mobile-panel" v-loading="loading">
      <el-tabs v-model="activeTab" class="todo-tabs">
        <el-tab-pane label="今日任务" name="today">
          <div class="todo-scroll">
            <el-empty v-if="todayRows.length === 0" description="今日任务为空" />
            <el-space v-else direction="vertical" fill :size="8" class="todo-list-wrap">
              <div v-for="row in todayRows" :key="`m-today-${row.id}`" class="todo-row">
                <div class="todo-main">
                  <div class="todo-title-line">
                    <el-checkbox
                      :model-value="row.status === 'DONE'"
                      :disabled="actionLoadingTodoId === row.id"
                      @change="(checked: unknown) => toggleTodoDone(row, Boolean(checked))"
                    />
                    <span class="todo-title">{{ row.title }}</span>
                  </div>
                </div>
                <el-button link type="warning" :loading="actionLoadingTodoId === row.id" @click="toggleTodayMembership(row, false)">撤销</el-button>
              </div>
            </el-space>
          </div>
        </el-tab-pane>

        <el-tab-pane label="全部任务" name="all">
          <div class="todo-scroll">
            <el-space class="bulk-actions" wrap>
              <el-button type="primary" plain size="small" @click="addAllToToday">全部加入今日</el-button>
              <el-button type="warning" plain size="small" @click="clearToday">撤销今日列表</el-button>
            </el-space>
            <el-space direction="vertical" fill :size="8" class="todo-list-wrap">
              <div v-for="row in allRows" :key="`m-all-${row.id}`" class="todo-row" :class="{ done: row.status === 'DONE' }">
                <div class="todo-main">
                  <div class="todo-title-line">
                    <span class="todo-title">{{ row.title }}</span>
                  </div>
                  <div class="todo-meta">
                    <span>{{ row.status === "DONE" ? "已完成" : "未完成" }}</span>
                  </div>
                </div>
                <el-button
                  v-if="row.status === 'OPEN'"
                  link
                  :type="row.is_in_today ? 'warning' : 'primary'"
                  :loading="actionLoadingTodoId === row.id"
                  @click="toggleTodayMembership(row, !row.is_in_today)"
                >
                  {{ row.is_in_today ? "撤销今日" : "加入今日" }}
                </el-button>
              </div>
            </el-space>
          </div>
        </el-tab-pane>

        <el-tab-pane label="系统待办" name="system">
          <div class="todo-scroll">
            <el-empty v-if="systemRows.length === 0" description="暂无系统待办" />
            <el-space v-else direction="vertical" fill :size="8" class="todo-list-wrap">
              <div v-for="item in systemRows" :key="`m-system-${item.id}`" class="todo-row system-row">
                <div class="todo-main">
                  <div class="todo-title-line">
                    <el-tag size="small" :type="item.module === 'BILLING' ? 'warning' : 'info'">
                      {{ item.module === "BILLING" ? "收款" : "线索" }}
                    </el-tag>
                    <span class="todo-title">{{ item.title }}</span>
                  </div>
                  <div class="todo-meta">
                    <span>截止 {{ formatTodoDate(item.due_date) }}</span>
                  </div>
                </div>
                <el-button link type="primary" @click="handleSystemAction(item)">
                  处理
                </el-button>
              </div>
            </el-space>
          </div>
        </el-tab-pane>
      </el-tabs>

      <div class="todo-footer mobile-footer">
        <el-form inline @submit.prevent="createTodo" class="todo-create-form mobile-create-form">
          <el-form-item>
            <el-input v-model="createForm.title" placeholder="添加任务" clearable @keyup.enter="createTodo" />
          </el-form-item>
          <el-form-item>
            <el-date-picker v-model="createForm.due_date" type="date" value-format="YYYY-MM-DD" placeholder="截止日" />
          </el-form-item>
          <el-form-item>
            <el-select v-model="createForm.priority" placeholder="优先级">
              <el-option label="高" value="HIGH" />
              <el-option label="中" value="MEDIUM" />
              <el-option label="低" value="LOW" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="creating" @click="createTodo">添加</el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </el-drawer>
</template>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.section-title {
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 6px;
}

.todo-toggle-btn {
  position: fixed;
  right: 14px;
  bottom: 18px;
  z-index: 1080;
  box-shadow: 0 8px 18px rgba(24, 100, 255, 0.25);
}

.todo-desktop-panel {
  position: fixed;
  right: 14px;
  bottom: 68px;
  z-index: 1080;
  width: min(400px, calc(100vw - 28px));
}

.todo-panel-body {
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 190px);
}

.todo-tabs {
  min-height: 0;
}

.todo-scroll {
  max-height: calc(100vh - 360px);
  overflow: auto;
  padding-right: 2px;
}

.todo-footer {
  border-top: 1px solid #eef2f7;
  margin-top: 8px;
  padding-top: 8px;
}

.todo-create-form :deep(.el-input),
.todo-create-form :deep(.el-select),
.todo-create-form :deep(.el-date-editor) {
  width: 100%;
}

.todo-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 8px;
  background: #fff;
}

.system-row {
  background: #f9fbff;
}

.todo-row.done {
  opacity: 0.75;
}

.todo-main {
  min-width: 0;
  flex: 1;
}

.todo-title-line {
  display: flex;
  align-items: center;
  gap: 6px;
}

.todo-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.todo-row.done .todo-title {
  text-decoration: line-through;
}

.todo-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
  color: #6b7280;
  font-size: 12px;
}

.todo-list-wrap {
  width: 100%;
}

.bulk-actions {
  margin-bottom: 8px;
}

.todo-fab {
  position: fixed;
  right: 12px;
  bottom: calc(env(safe-area-inset-bottom, 0px) + 12px);
  z-index: 1100;
  box-shadow: 0 8px 18px rgba(24, 100, 255, 0.25);
}

.mobile-panel {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.mobile-footer {
  margin-top: auto;
}

.mobile-create-form {
  display: flex;
  flex-wrap: wrap;
}

.mobile-create-form :deep(.el-form-item) {
  width: 100%;
  margin-right: 0;
}

.todo-slide-enter-active,
.todo-slide-leave-active {
  transition: all 0.2s ease;
}

.todo-slide-enter-from,
.todo-slide-leave-to {
  transform: translateX(12px);
  opacity: 0;
}

@media (max-width: 768px) {
  .todo-toggle-btn,
  .todo-desktop-panel {
    display: none;
  }

  .todo-fab {
    transform: scale(0.92);
    transform-origin: bottom right;
  }

  .todo-scroll {
    max-height: 52vh;
  }
}
</style>
