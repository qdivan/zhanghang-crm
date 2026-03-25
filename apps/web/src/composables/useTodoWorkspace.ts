import { ElMessage, ElMessageBox } from "element-plus";
import { computed, reactive, ref } from "vue";
import { useRouter } from "vue-router";

import { apiClient } from "../api/client";
import { mapPathForCurrentViewport } from "../mobile/config";
import type { SystemTodoItem, TodoCreatePayload, TodoItem } from "../types";

export function priorityLabel(priority: string): string {
  if (priority === "HIGH") return "高";
  if (priority === "LOW") return "低";
  return "中";
}

export function priorityTagType(priority: string): "danger" | "warning" | "info" {
  if (priority === "HIGH") return "danger";
  if (priority === "LOW") return "info";
  return "warning";
}

export function formatTodoDate(dateText: string | null | undefined): string {
  return dateText || "-";
}

export function useTodoWorkspace() {
  const router = useRouter();

  const activeTab = ref<"today" | "all" | "system">("today");
  const loading = ref(false);
  const creating = ref(false);
  const actionLoadingTodoId = ref<number | null>(null);
  const bulkActionLoading = ref<null | "add_today" | "clear_today" | "clear_done">(null);
  const allRows = ref<TodoItem[]>([]);
  const todayRows = ref<TodoItem[]>([]);
  const systemRows = ref<SystemTodoItem[]>([]);

  const createForm = reactive({
    title: "",
    due_date: "",
    priority: "MEDIUM" as "HIGH" | "MEDIUM" | "LOW",
  });

  const openManualCount = computed(() => allRows.value.filter((item) => item.status === "OPEN").length);
  const doneManualCount = computed(() => allRows.value.filter((item) => item.status === "DONE").length);

  async function fetchAllTodos() {
    const resp = await apiClient.get<TodoItem[]>("/todos", {
      params: { view: "ALL", include_done: true, limit: 300 },
    });
    allRows.value = resp.data;
  }

  async function fetchTodayTodos() {
    const resp = await apiClient.get<TodoItem[]>("/todos", {
      params: { view: "TODAY", limit: 300 },
    });
    todayRows.value = resp.data;
  }

  async function fetchSystemTodos() {
    const resp = await apiClient.get<SystemTodoItem[]>("/dashboard/system-todos", {
      params: { limit: 120 },
    });
    systemRows.value = resp.data;
  }

  async function refreshAll() {
    loading.value = true;
    try {
      await Promise.all([fetchAllTodos(), fetchTodayTodos(), fetchSystemTodos()]);
    } catch (error) {
      ElMessage.error("加载待办失败");
    } finally {
      loading.value = false;
    }
  }

  async function createTodo() {
    if (!createForm.title.trim()) {
      ElMessage.warning("请先填写待办标题");
      return;
    }
    const payload: TodoCreatePayload = {
      title: createForm.title.trim(),
      priority: createForm.priority,
      is_in_today: activeTab.value === "today",
    };
    if (createForm.due_date) {
      payload.due_date = createForm.due_date;
    }

    creating.value = true;
    try {
      await apiClient.post("/todos", payload);
      createForm.title = "";
      createForm.due_date = "";
      createForm.priority = "MEDIUM";
      await refreshAll();
      ElMessage.success("待办已添加");
    } catch (error) {
      ElMessage.error("新增待办失败");
    } finally {
      creating.value = false;
    }
  }

  async function toggleTodoDone(row: TodoItem, done: boolean) {
    actionLoadingTodoId.value = row.id;
    try {
      await apiClient.patch(`/todos/${row.id}`, {
        status: done ? "DONE" : "OPEN",
      });
      await refreshAll();
    } catch (error) {
      ElMessage.error("更新待办状态失败");
    } finally {
      actionLoadingTodoId.value = null;
    }
  }

  async function toggleTodayMembership(row: TodoItem, shouldBeInToday: boolean) {
    actionLoadingTodoId.value = row.id;
    try {
      await apiClient.patch(`/todos/${row.id}`, {
        is_in_today: shouldBeInToday,
      });
      await refreshAll();
    } catch (error) {
      ElMessage.error("更新今日任务失败");
    } finally {
      actionLoadingTodoId.value = null;
    }
  }

  async function addAllToToday() {
    bulkActionLoading.value = "add_today";
    try {
      const resp = await apiClient.post<{ affected_count: number }>("/todos/my-day/add-all");
      await refreshAll();
      ElMessage.success(`已加入今日 ${resp.data.affected_count} 条`);
    } catch (error) {
      ElMessage.error("批量加入今日失败");
    } finally {
      bulkActionLoading.value = null;
    }
  }

  async function clearToday() {
    bulkActionLoading.value = "clear_today";
    try {
      const resp = await apiClient.post<{ affected_count: number }>("/todos/my-day/clear");
      await refreshAll();
      ElMessage.success(`已撤销今日 ${resp.data.affected_count} 条`);
    } catch (error) {
      ElMessage.error("撤销今日失败");
    } finally {
      bulkActionLoading.value = null;
    }
  }

  async function clearCompletedTodos() {
    const doneRows = allRows.value.filter((item) => item.status === "DONE");
    if (!doneRows.length) {
      ElMessage.warning("当前没有已完成待办");
      return;
    }

    try {
      await ElMessageBox.confirm(`确认清理 ${doneRows.length} 条已完成待办吗？`, "清理已完成", {
        type: "warning",
        confirmButtonText: "确认清理",
        cancelButtonText: "取消",
      });
    } catch {
      return;
    }

    bulkActionLoading.value = "clear_done";
    try {
      const results = await Promise.allSettled(doneRows.map((row) => apiClient.delete(`/todos/${row.id}`)));
      const successCount = results.filter((item) => item.status === "fulfilled").length;
      const failedCount = doneRows.length - successCount;
      await refreshAll();
      if (failedCount === 0) {
        ElMessage.success(`已清理 ${successCount} 条已完成待办`);
        return;
      }
      if (successCount > 0) {
        ElMessage.warning(`已清理 ${successCount} 条，另有 ${failedCount} 条失败`);
        return;
      }
      ElMessage.error("清理已完成待办失败");
    } catch (error) {
      ElMessage.error("清理已完成待办失败");
    } finally {
      bulkActionLoading.value = null;
    }
  }

  async function removeTodo(row: TodoItem) {
    try {
      await ElMessageBox.confirm(`确认删除待办“${row.title}”吗？`, "删除待办", {
        type: "warning",
        confirmButtonText: "删除",
        cancelButtonText: "取消",
      });
    } catch {
      return;
    }

    actionLoadingTodoId.value = row.id;
    try {
      await apiClient.delete(`/todos/${row.id}`);
      await refreshAll();
      ElMessage.success("待办已删除");
    } catch (error) {
      ElMessage.error("删除待办失败");
    } finally {
      actionLoadingTodoId.value = null;
    }
  }

  async function openSystemAction(row: SystemTodoItem) {
    const targetPath = mapPathForCurrentViewport(row.action_path);
    await router.push(targetPath);
  }

  return {
    activeTab,
    loading,
    creating,
    actionLoadingTodoId,
    bulkActionLoading,
    allRows,
    todayRows,
    systemRows,
    createForm,
    openManualCount,
    doneManualCount,
    refreshAll,
    createTodo,
    toggleTodoDone,
    toggleTodayMembership,
    addAllToToday,
    clearToday,
    clearCompletedTodos,
    removeTodo,
    openSystemAction,
  };
}
