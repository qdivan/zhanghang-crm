import { ElMessage, ElMessageBox } from "element-plus";
import { computed, reactive, ref } from "vue";
import { useRouter } from "vue-router";

import { apiClient } from "../api/client";
import { mapPathForCurrentViewport } from "../mobile/config";
import { useAuthStore } from "../stores/auth";
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
  const auth = useAuthStore();

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

  const manualCounts = computed(() => {
    let open = 0;
    let done = 0;
    for (const item of allRows.value) {
      if (item.status === "DONE") {
        done += 1;
        continue;
      }
      open += 1;
    }
    return { open, done };
  });
  const openManualCount = computed(() => manualCounts.value.open);
  const doneManualCount = computed(() => manualCounts.value.done);
  const canDeleteTodos = computed(() => auth.user?.role === "OWNER" || auth.user?.role === "ADMIN");

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
    if (!canDeleteTodos.value) {
      ElMessage.warning("只有老板和管理员可以删除待办");
      return;
    }
    const doneRows = allRows.value.filter((item) => item.status === "DONE");
    if (!doneRows.length) {
      ElMessage.warning("当前没有已完成待办");
      return;
    }
    ElMessage.info("已完成待办请逐条删除。删除时需要输入待办名称确认。");
  }

  async function removeTodo(row: TodoItem) {
    if (!canDeleteTodos.value) {
      ElMessage.warning("只有老板和管理员可以删除待办");
      return;
    }
    const expectedName = (row.title || "").trim() || `待办#${row.id}`;
    try {
      const result = (await ElMessageBox.prompt(`请输入“${expectedName}”确认删除这条待办。`, "删除待办", {
        type: "warning",
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        inputPlaceholder: expectedName,
      })) as { value: string };
      if ((result.value || "").trim() !== expectedName) {
        ElMessage.warning("输入名称不一致，已取消删除");
        return;
      }
    } catch {
      return;
    }

    actionLoadingTodoId.value = row.id;
    try {
      await apiClient.delete(`/todos/${row.id}`, {
        params: { confirm_name: expectedName },
      });
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
    canDeleteTodos,
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
