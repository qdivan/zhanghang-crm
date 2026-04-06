<script setup lang="ts">
import { Calendar, CollectionTag, DocumentAdd, Files, House, Management, Money, RefreshRight } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { apiClient } from "../../api/client";
import {
  formatTodoDate,
  priorityLabel,
  priorityTagType,
  useTodoWorkspace,
} from "../../composables/useTodoWorkspace";
import { mapPathForCurrentViewport } from "../../mobile/config";
import { scheduleMobileTodoIdlePrefetch } from "../../mobile/prefetch";
import { useAuthStore } from "../../stores/auth";
import type { DashboardSummary, SystemTodoItem, TodoItem } from "../../types";

type SystemTodoGroup = {
  key: SystemTodoItem["module"];
  label: string;
  copy: string;
  queuePath: string;
  queueLabel: string;
  rows: SystemTodoItem[];
};

type FocusPanelActionMode = "today_high" | "all_high" | "pending_today" | null;
type ProcessingEntryTone = "quiet" | "accent" | "warning" | "danger";
type ProcessingEntry = {
  key: "lead-queue" | "billing-queue";
  label: string;
  value: string;
  meta: string;
  summary: string;
  path: string;
  disabled: boolean;
  tone: ProcessingEntryTone;
  pressure: number;
};

type AttentionEntry = {
  key: "receipt-reconciliation" | "costs";
  label: string;
  meta: string;
  path: string;
  tone: ProcessingEntryTone;
  icon: typeof Money | typeof CollectionTag;
  pressure: number;
};

type TodoManualInsights = {
  sortedTodayRows: TodoItem[];
  sortedAllRows: TodoItem[];
  todayHighPriorityCount: number;
  allHighPriorityCount: number;
  openHighPriorityCount: number;
  allDoneRows: TodoItem[];
  allPendingTodayRows: TodoItem[];
};

type TodoSystemInsights = {
  leadCount: number;
  billingCount: number;
};

const auth = useAuthStore();
const router = useRouter();
const {
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
  removeTodo,
  openSystemAction,
} = useTodoWorkspace();

const dashboardSummary = ref<DashboardSummary>({
  month: "",
  lead_new_count: 0,
  lead_following_count: 0,
  customer_count: 0,
  billing_record_count: 0,
  outstanding_amount_total: 0,
  manual_open_todo_count: 0,
  system_todo_count: 0,
});

const summaryLoading = ref(false);
const workspaceReady = ref(false);
const todayManualFocus = ref<"all" | "high">("all");
const allManualFocus = ref<"all" | "high" | "pending_today" | "done">("all");

function todoPriorityRank(priority: TodoItem["priority"]) {
  if (priority === "HIGH") return 0;
  if (priority === "MEDIUM") return 1;
  return 2;
}

function todoDueRank(dateText: string | null) {
  if (!dateText) return Number.MAX_SAFE_INTEGER;
  const date = new Date(`${dateText}T00:00:00`);
  return Number.isNaN(date.getTime()) ? Number.MAX_SAFE_INTEGER : date.getTime();
}

function sortManualRows(rows: TodoItem[]) {
  return [...rows].sort((left, right) => {
    if (left.status !== right.status) return left.status === "OPEN" ? -1 : 1;
    const priorityDiff = todoPriorityRank(left.priority) - todoPriorityRank(right.priority);
    if (priorityDiff !== 0) return priorityDiff;
    const dueDiff = todoDueRank(left.due_date) - todoDueRank(right.due_date);
    if (dueDiff !== 0) return dueDiff;
    return right.id - left.id;
  });
}

const manualRowInsights = computed<TodoManualInsights>(() => {
  const sortedTodayRows = sortManualRows(todayRows.value);
  const sortedAllRows = sortManualRows(allRows.value);

  let todayHighPriorityCount = 0;
  for (const row of todayRows.value) {
    if (row.priority === "HIGH") {
      todayHighPriorityCount += 1;
    }
  }

  let allHighPriorityCount = 0;
  let openHighPriorityCount = 0;
  const allDoneRows: TodoItem[] = [];
  const allPendingTodayRows: TodoItem[] = [];

  for (const row of sortedAllRows) {
    if (row.priority === "HIGH") {
      allHighPriorityCount += 1;
      if (row.status === "OPEN") {
        openHighPriorityCount += 1;
      }
    }
    if (row.status === "DONE") {
      allDoneRows.push(row);
      continue;
    }
    if (!row.is_in_today) {
      allPendingTodayRows.push(row);
    }
  }

  return {
    sortedTodayRows,
    sortedAllRows,
    todayHighPriorityCount,
    allHighPriorityCount,
    openHighPriorityCount,
    allDoneRows,
    allPendingTodayRows,
  };
});

const sortedTodayRows = computed(() => manualRowInsights.value.sortedTodayRows);
const sortedAllRows = computed(() => manualRowInsights.value.sortedAllRows);
const todayHighPriorityCount = computed(() => manualRowInsights.value.todayHighPriorityCount);
const allHighPriorityCount = computed(() => manualRowInsights.value.allHighPriorityCount);
const openHighPriorityCount = computed(() => manualRowInsights.value.openHighPriorityCount);

const activeRows = computed(() => {
  if (activeTab.value === "today") return visibleManualRows.value;
  if (activeTab.value === "all") return visibleManualRows.value;
  return systemRows.value;
});

async function fetchDashboardSummary() {
  summaryLoading.value = true;
  try {
    const resp = await apiClient.get<DashboardSummary>("/dashboard/summary");
    dashboardSummary.value = resp.data;
  } catch (error) {
    ElMessage.error("加载工作台摘要失败");
  } finally {
    summaryLoading.value = false;
  }
}

async function refreshWorkspace() {
  await Promise.all([refreshAll(), fetchDashboardSummary()]);
}

async function bootstrapWorkspace() {
  try {
    await refreshWorkspace();
  } finally {
    workspaceReady.value = true;
  }
}

function goTo(path: string) {
  router.push(mapPathForCurrentViewport(path));
}

function formatMetricValue(value: number): string {
  const amount = Number(value || 0);
  return amount.toLocaleString("zh-CN", {
    minimumFractionDigits: Number.isInteger(amount) ? 0 : 2,
    maximumFractionDigits: 2,
  });
}

const focusPanel = computed(() => {
  if (systemRows.value.length > 0) {
    return {
      label: "先处理系统提醒",
      detail: "有系统动作等待进入业务页面处理。",
      value: systemRows.value.length,
      tone: "warning",
      actionLabel: "",
      actionMode: null as FocusPanelActionMode,
    };
  }
  if (todayHighPriorityCount.value > 0) {
    return {
      label: "高优先任务先处理",
      detail: `今日有 ${todayHighPriorityCount.value} 条高优先任务，先集中推进。`,
      value: todayHighPriorityCount.value,
      tone: "danger",
      actionLabel: "只看高优先",
      actionMode: "today_high" as FocusPanelActionMode,
    };
  }
  if (openHighPriorityCount.value > 0) {
    return {
      label: "高优先任务待拉入今日",
      detail: `${openHighPriorityCount.value} 条高优先任务还没进今日，建议先收口。`,
      value: openHighPriorityCount.value,
      tone: "warning",
      actionLabel: "查看高优先",
      actionMode: "all_high" as FocusPanelActionMode,
    };
  }
  if (todayRows.value.length > 0) {
    return {
      label: "今日任务在推进",
      detail: "先完成今天要推进的事，再切到其他模块。",
      value: todayRows.value.length,
      tone: "accent",
      actionLabel: "",
      actionMode: null as FocusPanelActionMode,
    };
  }
  if (openManualCount.value > 0) {
    return {
      label: "开放任务待分配",
      detail: "把最重要的任务加入今日清单，减少分心。",
      value: openManualCount.value,
      tone: "neutral",
      actionLabel: allPendingTodayCount.value > 0 ? "查看待加入今日" : "",
      actionMode: allPendingTodayCount.value > 0 ? ("pending_today" as FocusPanelActionMode) : null,
    };
  }
  return {
    label: "当前没有待办压力",
    detail: "可以补充新任务，或直接进入开发、客户、收费。",
    value: 0,
    tone: "quiet",
    actionLabel: "",
    actionMode: null as FocusPanelActionMode,
  };
});

const signalChips = computed(() => [
  { label: "今日", value: formatMetricValue(todayRows.value.length), accent: todayRows.value.length > 0 },
  { label: "系统", value: formatMetricValue(systemRows.value.length), warning: systemRows.value.length > 0 },
  { label: "跟进", value: formatMetricValue(dashboardSummary.value.lead_following_count) },
  {
    label: "未收",
    value: formatMetricValue(dashboardSummary.value.outstanding_amount_total),
    danger: dashboardSummary.value.outstanding_amount_total > 0,
  },
]);
const showWorkspaceSkeleton = computed(() => !workspaceReady.value);
const showSummaryOverlay = computed(() => summaryLoading.value && workspaceReady.value);
const showTodoListOverlay = computed(() => loading.value && workspaceReady.value);

const systemTodoInsights = computed<TodoSystemInsights>(() => {
  let leadCount = 0;
  let billingCount = 0;
  for (const row of systemRows.value) {
    if (row.module === "LEAD") {
      leadCount += 1;
      continue;
    }
    if (row.module === "BILLING") {
      billingCount += 1;
    }
  }
  return { leadCount, billingCount };
});

const leadSystemTodoCount = computed(() => systemTodoInsights.value.leadCount);
const billingSystemTodoCount = computed(() => systemTodoInsights.value.billingCount);

const quickEntries = computed(() => [
  {
    label: "开发",
    value: formatMetricValue(dashboardSummary.value.lead_new_count + dashboardSummary.value.lead_following_count),
    meta: `跟进中 ${formatMetricValue(dashboardSummary.value.lead_following_count)}`,
    icon: Management,
    path: "/m/leads",
  },
  {
    label: "客户",
    value: formatMetricValue(dashboardSummary.value.customer_count),
    meta: "继续维护和补记录",
    icon: House,
    path: "/m/customers",
  },
  {
    label: "收费",
    value: formatMetricValue(dashboardSummary.value.billing_record_count),
    meta: `未收 ${formatMetricValue(dashboardSummary.value.outstanding_amount_total)}`,
    icon: Money,
    path: "/m/billing",
  },
]);

const processingEntries = computed<ProcessingEntry[]>(() => {
  const leadPressure = leadSystemTodoCount.value * 10 + dashboardSummary.value.lead_following_count;
  const billingPressure =
    billingSystemTodoCount.value * 10 +
    (dashboardSummary.value.outstanding_amount_total > 0 ? 5 : 0) +
    (dashboardSummary.value.billing_record_count > 0 ? 1 : 0);

  const entries: ProcessingEntry[] = [
    {
      key: "lead-queue",
      label: "连续跟进",
      value: `${formatMetricValue(dashboardSummary.value.lead_following_count)} 条`,
      meta:
        leadSystemTodoCount.value > 0
          ? `系统提醒 ${formatMetricValue(leadSystemTodoCount.value)} 条`
          : "打开跟进中队列，从首条开始。",
      summary:
        leadSystemTodoCount.value > 0
          ? `开发提醒有 ${leadSystemTodoCount.value} 条，先连续扫完跟进中的线索。`
          : "把跟进中的线索连续处理完，减少来回切换。",
      path: "/leads?queue=followup",
      disabled: dashboardSummary.value.lead_following_count <= 0,
      tone: leadSystemTodoCount.value > 0 ? "warning" : dashboardSummary.value.lead_following_count > 0 ? "accent" : "quiet",
      pressure: dashboardSummary.value.lead_following_count <= 0 ? 0 : leadPressure,
    },
    {
      key: "billing-queue",
      label: "连续催收",
      value: `未收 ${formatMetricValue(dashboardSummary.value.outstanding_amount_total)}`,
      meta:
        billingSystemTodoCount.value > 0
          ? `系统提醒 ${formatMetricValue(billingSystemTodoCount.value)} 条`
          : "打开未收收费队列，逐条登记催收或收款。",
      summary:
        billingSystemTodoCount.value > 0
          ? `收费提醒有 ${billingSystemTodoCount.value} 条，先集中处理催收和续费。`
          : "把未收收费连续处理完，优先登记催收和收款。",
      path: "/billing?queue=activity",
      disabled: dashboardSummary.value.outstanding_amount_total <= 0,
      tone:
        billingSystemTodoCount.value > 0 && dashboardSummary.value.outstanding_amount_total > 0
          ? "danger"
          : billingSystemTodoCount.value > 0
            ? "warning"
            : dashboardSummary.value.outstanding_amount_total > 0
              ? "accent"
              : "quiet",
      pressure: dashboardSummary.value.outstanding_amount_total <= 0 ? 0 : billingPressure,
    },
  ];

  return entries.sort((left, right) => right.pressure - left.pressure);
});

const processingSpotlight = computed(() => {
  return processingEntries.value.find((item) => !item.disabled && item.pressure > 0) ?? null;
});

const attentionEntries = computed<AttentionEntry[]>(() => {
  const entries: AttentionEntry[] = [];
  const canViewReceiptReconciliation =
    auth.user?.role === "OWNER" ||
    auth.user?.role === "ADMIN" ||
    auth.user?.role === "MANAGER" ||
    Boolean(auth.user?.granted_read_modules.includes("BILLING"));

  if (canViewReceiptReconciliation && (billingSystemTodoCount.value > 0 || dashboardSummary.value.outstanding_amount_total > 0)) {
    entries.push({
      key: "receipt-reconciliation",
      label: "到账核对",
      meta:
        billingSystemTodoCount.value > 0
          ? `收费提醒 ${billingSystemTodoCount.value} 条，先去核对到账和账户流水。`
          : `未收 ${formatMetricValue(dashboardSummary.value.outstanding_amount_total)}，建议先核对到账记录。`,
      path: "/m/receipt-reconciliation",
      tone:
        billingSystemTodoCount.value > 0 && dashboardSummary.value.outstanding_amount_total > 0
          ? "danger"
          : billingSystemTodoCount.value > 0
            ? "warning"
            : "accent",
      icon: Money,
      pressure: billingSystemTodoCount.value * 10 + (dashboardSummary.value.outstanding_amount_total > 0 ? 5 : 0),
    });
  }

  if (auth.user?.role === "OWNER" && dashboardSummary.value.outstanding_amount_total > 0) {
    entries.push({
      key: "costs",
      label: "成本与老板视图",
      meta: `未收 ${formatMetricValue(dashboardSummary.value.outstanding_amount_total)}，老板视角可直接复盘成本与回款压力。`,
      path: "/m/costs",
      tone: dashboardSummary.value.outstanding_amount_total > 0 ? "warning" : "quiet",
      icon: CollectionTag,
      pressure: dashboardSummary.value.outstanding_amount_total > 0 ? 4 : 0,
    });
  }

  return entries.sort((left, right) => right.pressure - left.pressure);
});

const systemTodoGroups = computed<SystemTodoGroup[]>(() => {
  const order: SystemTodoItem["module"][] = ["LEAD", "BILLING", "CUSTOMER"];
  return order
    .map((module) => {
      const rows = systemRows.value.filter((item) => item.module === module);
      if (!rows.length) return null;
      return {
        key: module,
        label: systemTodoModuleLabel(module),
        copy: systemTodoGroupCopy(module, rows),
        queuePath: systemTodoModuleQueuePath(module),
        queueLabel: systemTodoModuleQueueLabel(module),
        rows,
      };
    })
    .filter((group): group is SystemTodoGroup => Boolean(group));
});

const activePanelTitle = computed(() => {
  if (activeTab.value === "system") return "系统提醒";
  if (activeTab.value === "today") return "今日任务";
  return "全部任务";
});

const activePanelCopy = computed(() => {
  if (activeTab.value === "system") return "直接进入开发、客户或收费页面处理动作。";
  if (activeTab.value === "today") return "只保留今天真正要推进的事。";
  return "开放任务集中在这里，再挑重点加入今日。";
});

const allDoneRows = computed(() => manualRowInsights.value.allDoneRows);
const allPendingTodayCount = computed(() => manualRowInsights.value.allPendingTodayRows.length);
const showAllBulkPanel = computed(() => activeTab.value === "all" && (allRows.value.length > 0 || doneManualCount.value > 0));
const manualFocusOptions = computed(() => {
  if (activeTab.value === "today") {
    return [
      { key: "all" as const, label: "全部", count: sortedTodayRows.value.length },
      { key: "high" as const, label: "高优先", count: todayHighPriorityCount.value },
    ];
  }
  if (activeTab.value === "all") {
    return [
      { key: "all" as const, label: "全部", count: sortedAllRows.value.length },
      { key: "high" as const, label: "高优先", count: allHighPriorityCount.value },
      { key: "pending_today" as const, label: "待加入今日", count: allPendingTodayCount.value },
      { key: "done" as const, label: "已完成", count: allDoneRows.value.length },
    ];
  }
  return [];
});
const activeManualFocusKey = computed(() => (activeTab.value === "today" ? todayManualFocus.value : allManualFocus.value));
const visibleManualRows = computed(() => {
  if (activeTab.value === "today") {
    if (todayManualFocus.value === "high") {
      return sortedTodayRows.value.filter((row) => row.priority === "HIGH");
    }
    return sortedTodayRows.value;
  }
  if (activeTab.value === "all") {
    if (allManualFocus.value === "high") {
      return sortedAllRows.value.filter((row) => row.priority === "HIGH");
    }
    if (allManualFocus.value === "pending_today") {
      return sortedAllRows.value.filter((row) => row.status === "OPEN" && !row.is_in_today);
    }
    if (allManualFocus.value === "done") {
      return sortedAllRows.value.filter((row) => row.status === "DONE");
    }
    return sortedAllRows.value;
  }
  return [];
});
const manualFocusHint = computed(() => {
  if (activeTab.value === "today" && todayManualFocus.value === "high") return "仅看今日高优先级任务。";
  if (activeTab.value === "all" && allManualFocus.value === "high") return "仅看全部任务里的高优先级项。";
  if (activeTab.value === "all" && allManualFocus.value === "pending_today") return "只看还没加入今日的开放任务。";
  if (activeTab.value === "all" && allManualFocus.value === "done") return "只看已经完成的待办，便于批量清理。";
  return "按优先级和截止日排序。";
});
const manualEmptyMessage = computed(() => {
  if (activeTab.value === "today" && todayManualFocus.value === "high") return "当前没有高优先级今日任务";
  if (activeTab.value === "today") return "今日任务为空";
  if (activeTab.value === "all" && allManualFocus.value === "high") return "当前没有高优先级待办";
  if (activeTab.value === "all" && allManualFocus.value === "pending_today") return "当前没有待加入今日的任务";
  if (activeTab.value === "all" && allManualFocus.value === "done") return "当前没有已完成待办";
  return "暂无手动任务";
});
const systemEmptyState = computed(() => ({
  kicker: "系统提醒",
  title: "当前没有待处理动作",
  copy: "可以先回到今日任务，或直接进入开发、客户、收费页面。",
}));
const manualEmptyState = computed(() => {
  if (activeTab.value === "today" && todayManualFocus.value === "high") {
    return {
      kicker: "今日任务",
      title: manualEmptyMessage.value,
      copy: "高优先项已经清空，可以切回全部任务继续推进。",
    };
  }
  if (activeTab.value === "today") {
    return {
      kicker: "今日任务",
      title: manualEmptyMessage.value,
      copy: "把最重要的开放任务加入今日，保持清单足够轻。",
    };
  }
  if (activeTab.value === "all" && allManualFocus.value === "high") {
    return {
      kicker: "全部任务",
      title: manualEmptyMessage.value,
      copy: "当前开放任务里没有高优先项，可以回到全部视图继续筛选。",
    };
  }
  if (activeTab.value === "all" && allManualFocus.value === "pending_today") {
    return {
      kicker: "全部任务",
      title: manualEmptyMessage.value,
      copy: "开放任务都已经进入今日，当前清单比较干净。",
    };
  }
  if (activeTab.value === "all" && allManualFocus.value === "done") {
    return {
      kicker: "全部任务",
      title: manualEmptyMessage.value,
      copy: "没有可清理的已完成项，继续保留当前任务池即可。",
    };
  }
  return {
    kicker: "全部任务",
    title: manualEmptyMessage.value,
    copy: "现在可以直接补充新任务，或从业务页面带回新的待办。",
  };
});

function setManualFocus(key: "all" | "high" | "pending_today" | "done") {
  if (activeTab.value === "today") {
    todayManualFocus.value = key === "high" ? "high" : "all";
    return;
  }
  if (activeTab.value === "all") {
    allManualFocus.value = key;
  }
}

function applyFocusPanelAction(mode: FocusPanelActionMode) {
  if (!mode) return;
  if (mode === "today_high") {
    activeTab.value = "today";
    todayManualFocus.value = "high";
    return;
  }
  activeTab.value = "all";
  allManualFocus.value = mode === "all_high" ? "high" : "pending_today";
}

function todoRowMeta(row: TodoItem) {
  const meta = [`截止 ${formatTodoDate(row.due_date)}`];
  if (row.status === "DONE") {
    meta.push("已完成");
  } else if (row.is_in_today) {
    meta.push("今日");
  }
  return meta.join(" · ");
}

function systemTodoMeta(row: SystemTodoItem) {
  return [systemTodoModuleLabel(row.module), `截止 ${formatTodoDate(row.due_date)}`].join(" · ");
}

function systemTodoModuleLabel(module: SystemTodoItem["module"]) {
  return module === "BILLING" ? "收费" : module === "CUSTOMER" ? "客户" : "开发";
}

function systemTodoModuleQueuePath(module: SystemTodoItem["module"]): string {
  if (module === "LEAD") return "/leads?queue=followup";
  if (module === "BILLING") return "/billing?queue=activity";
  return "";
}

function systemTodoModuleQueueLabel(module: SystemTodoItem["module"]): string {
  if (module === "LEAD") return "开始连续跟进";
  if (module === "BILLING") return "开始连续催收";
  return "";
}

function isBillingRenewTodo(row: SystemTodoItem): boolean {
  return row.module === "BILLING" && /(?:^|[?&])action=renew(?:&|$)/.test(row.action_path || "");
}

function systemTodoPrimaryLabel(row: SystemTodoItem): string {
  if (row.module === "LEAD") return "处理这条线索";
  if (row.module === "CUSTOMER") return "打开客户档案";
  if (isBillingRenewTodo(row)) return "处理这条续费";
  if (row.module === "BILLING") return "打开收费台账";
  return row.action_label || "处理";
}

function systemTodoGroupCopy(module: SystemTodoItem["module"], rows: SystemTodoItem[]): string {
  if (module === "LEAD") return "本组集中处理需要回访的线索。";
  if (module === "BILLING") {
    return rows.some(isBillingRenewTodo) ? "催收和续费提醒都在这里。" : "未收和到期提醒都在这里。";
  }
  return "客户提醒以单条事项处理为主。";
}

function systemTodoActionNote(row: SystemTodoItem): string {
  if (row.module === "LEAD") return "单条进入当前线索。";
  if (isBillingRenewTodo(row)) return "单条确认当前续费。";
  if (row.module === "BILLING") return "单条进入当前收费单。";
  return "单条进入当前客户事项。";
}

onMounted(() => {
  void bootstrapWorkspace();
  scheduleMobileTodoIdlePrefetch();
});
</script>

<template>
  <section class="mobile-page mobile-todo-page">
    <section class="mobile-hero-block" v-loading="showSummaryOverlay">
      <template v-if="showWorkspaceSkeleton">
        <div class="mobile-section-title-row">
          <div class="mobile-skeleton-stack todo-skeleton-copy">
            <div class="mobile-skeleton-line is-xs"></div>
            <div class="mobile-skeleton-line is-lg"></div>
            <div class="mobile-skeleton-line is-xl"></div>
          </div>
          <div class="mobile-skeleton-circle"></div>
        </div>

        <div class="mobile-hero-stack todo-hero-skeleton-stack">
          <div class="todo-skeleton-focus">
            <div class="mobile-skeleton-stack">
              <div class="mobile-skeleton-line is-sm"></div>
              <div class="mobile-skeleton-line is-md"></div>
            </div>
            <div class="mobile-skeleton-stack todo-skeleton-focus-side">
              <div class="mobile-skeleton-line is-xs"></div>
              <div class="mobile-skeleton-line is-xs"></div>
            </div>
          </div>

          <div class="mobile-signal-row">
            <div v-for="index in 4" :key="`todo-signal-${index}`" class="todo-skeleton-signal">
              <div class="mobile-skeleton-line is-xs"></div>
              <div class="mobile-skeleton-line is-sm"></div>
            </div>
          </div>

          <div class="mobile-quick-links">
            <div v-for="index in 3" :key="`todo-link-${index}`" class="todo-skeleton-link">
              <div class="mobile-skeleton-circle"></div>
              <div class="mobile-skeleton-stack todo-skeleton-link-copy">
                <div class="mobile-skeleton-line is-xs"></div>
                <div class="mobile-skeleton-line is-sm"></div>
                <div class="mobile-skeleton-line is-md"></div>
              </div>
            </div>
          </div>

          <div class="todo-skeleton-spotlight">
            <div class="mobile-skeleton-stack todo-skeleton-spotlight-copy">
              <div class="mobile-skeleton-line is-xs"></div>
              <div class="mobile-skeleton-line is-md"></div>
              <div class="mobile-skeleton-line is-lg"></div>
            </div>
            <div class="mobile-skeleton-button"></div>
          </div>

          <div class="mobile-processing-strip">
            <div v-for="index in 2" :key="`todo-processing-${index}`" class="todo-skeleton-processing">
              <div class="mobile-skeleton-row">
                <div class="mobile-skeleton-line is-xs"></div>
                <div class="mobile-skeleton-line is-xs"></div>
              </div>
              <div class="mobile-skeleton-line is-md"></div>
            </div>
          </div>
        </div>
      </template>

      <template v-else>
        <div class="mobile-section-title-row">
          <div>
            <div class="mobile-section-eyebrow">{{ dashboardSummary.month || "本月" }} 工作台</div>
            <div class="mobile-section-title">{{ focusPanel.label }}</div>
            <div class="mobile-section-copy">{{ focusPanel.detail }}</div>
          </div>
          <el-button circle plain size="small" @click="refreshWorkspace">
            <el-icon><RefreshRight /></el-icon>
          </el-button>
        </div>

        <div class="mobile-hero-stack">
          <div class="mobile-focus-strip" :class="focusPanel.tone">
            <div class="mobile-focus-main">
              <span class="mobile-focus-label">{{ focusPanel.label }}</span>
              <strong class="mobile-focus-value">{{ formatMetricValue(focusPanel.value) }}</strong>
            </div>
            <div class="mobile-focus-meta">
              <span>开放 {{ formatMetricValue(openManualCount) }}</span>
              <span>已完成 {{ formatMetricValue(doneManualCount) }}</span>
              <el-button
                v-if="focusPanel.actionLabel"
                text
                size="small"
                type="primary"
                class="mobile-focus-action"
                @click="applyFocusPanelAction(focusPanel.actionMode)"
              >
                {{ focusPanel.actionLabel }}
              </el-button>
            </div>
          </div>

          <div class="mobile-signal-row">
            <article
              v-for="item in signalChips"
              :key="item.label"
              class="mobile-signal-chip"
              :class="{ accent: item.accent, warning: item.warning, danger: item.danger }"
            >
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </article>
          </div>

          <div class="mobile-quick-links">
            <button
              v-for="entry in quickEntries"
              :key="entry.path"
              type="button"
              class="mobile-quick-link"
              @click="goTo(entry.path)"
            >
              <component :is="entry.icon" class="mobile-quick-link-icon" />
              <div class="mobile-quick-link-copy">
                <span>{{ entry.label }}</span>
                <strong>{{ entry.value }}</strong>
                <small>{{ entry.meta }}</small>
              </div>
            </button>
          </div>

          <div
            v-if="processingSpotlight"
            class="mobile-processing-spotlight"
            :class="processingSpotlight.tone"
          >
            <div class="mobile-processing-spotlight-main">
              <div class="mobile-processing-spotlight-kicker">当前最急</div>
              <div class="mobile-processing-spotlight-title">{{ processingSpotlight.label }}</div>
              <div class="mobile-processing-spotlight-copy">{{ processingSpotlight.summary }}</div>
            </div>
            <el-button
              size="small"
              :type="processingSpotlight.tone === 'danger' ? 'danger' : 'primary'"
              @click="goTo(processingSpotlight.path)"
            >
              立即处理
            </el-button>
          </div>

          <div class="mobile-processing-strip">
            <button
              v-for="entry in processingEntries"
              :key="entry.key"
              type="button"
              class="mobile-processing-link"
              :class="[entry.tone, { disabled: entry.disabled, priority: processingSpotlight?.key === entry.key }]"
              :disabled="entry.disabled"
              @click="goTo(entry.path)"
            >
              <div class="mobile-processing-main">
                <span>{{ entry.label }}</span>
                <strong>{{ entry.value }}</strong>
              </div>
              <small>{{ entry.meta }}</small>
            </button>
          </div>

          <div v-if="attentionEntries.length" class="mobile-attention-strip">
            <button
              v-for="entry in attentionEntries"
              :key="entry.key"
              type="button"
              class="mobile-attention-link"
              :class="entry.tone"
              @click="goTo(entry.path)"
            >
              <div class="mobile-attention-main">
                <component :is="entry.icon" class="mobile-attention-icon" />
                <div>
                  <div class="mobile-attention-title">{{ entry.label }}</div>
                  <div class="mobile-attention-copy">{{ entry.meta }}</div>
                </div>
              </div>
            </button>
          </div>
        </div>
      </template>
    </section>

    <section class="mobile-work-panel">
      <template v-if="showWorkspaceSkeleton">
        <div class="mobile-work-head">
          <div class="mobile-skeleton-stack todo-skeleton-copy">
            <div class="mobile-skeleton-line is-md"></div>
            <div class="mobile-skeleton-line is-lg"></div>
          </div>
          <div class="mobile-skeleton-chip"></div>
        </div>

        <div class="mobile-work-stack">
          <div class="todo-skeleton-segmented">
            <div v-for="index in 3" :key="`todo-segment-${index}`" class="mobile-skeleton-button"></div>
          </div>
          <div class="mobile-skeleton-row todo-skeleton-inline-summary">
            <div v-for="index in 3" :key="`todo-inline-${index}`" class="mobile-skeleton-line is-sm"></div>
          </div>
          <div class="mobile-create-block">
            <div class="todo-skeleton-create-bar">
              <div class="mobile-skeleton-line is-full"></div>
              <div class="mobile-skeleton-button"></div>
            </div>
            <div class="todo-skeleton-create-tools">
              <div class="mobile-skeleton-line is-full"></div>
              <div class="mobile-skeleton-line is-full"></div>
            </div>
          </div>
          <div class="mobile-list-stack todo-skeleton-list">
            <div v-for="index in 4" :key="`todo-row-${index}`" class="todo-skeleton-row">
              <div class="mobile-skeleton-row">
                <div class="mobile-skeleton-circle todo-skeleton-checkbox"></div>
                <div class="mobile-skeleton-stack todo-skeleton-row-copy">
                  <div class="mobile-skeleton-line is-lg"></div>
                  <div class="mobile-skeleton-line is-md"></div>
                </div>
                <div class="mobile-skeleton-chip"></div>
              </div>
              <div class="mobile-skeleton-row todo-skeleton-row-actions">
                <div class="mobile-skeleton-button"></div>
                <div class="mobile-skeleton-button"></div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <template v-else>
        <div class="mobile-work-head">
          <div>
            <div class="mobile-section-title">{{ activePanelTitle }}</div>
            <div class="mobile-section-copy">{{ activePanelCopy }}</div>
          </div>
          <el-tag class="mobile-count-tag" size="small" effect="plain">{{ activeRows.length }} 条</el-tag>
        </div>

        <div class="mobile-work-stack">
          <div class="mobile-segmented">
            <button type="button" :class="{ active: activeTab === 'today' }" @click="activeTab = 'today'">
              今日 {{ todayRows.length }}
            </button>
            <button type="button" :class="{ active: activeTab === 'all' }" @click="activeTab = 'all'">
              全部 {{ openManualCount }}
            </button>
            <button type="button" :class="{ active: activeTab === 'system' }" @click="activeTab = 'system'">
              系统 {{ systemRows.length }}
            </button>
          </div>

          <div class="mobile-inline-summary">
            <span>开放任务 {{ openManualCount }}</span>
            <span>已完成 {{ doneManualCount }}</span>
            <span>系统提醒 {{ dashboardSummary.system_todo_count }}</span>
          </div>

          <div class="mobile-create-block">
            <div class="mobile-create-bar">
              <el-input
                v-model="createForm.title"
                placeholder="添加新任务"
                clearable
                @keyup.enter="createTodo"
              />
              <el-button type="primary" :icon="DocumentAdd" :loading="creating" @click="createTodo">添加</el-button>
            </div>
            <div class="mobile-create-tools">
              <el-date-picker
                v-model="createForm.due_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="截止日"
              />
              <el-select v-model="createForm.priority" placeholder="优先级">
                <el-option label="高" value="HIGH" />
                <el-option label="中" value="MEDIUM" />
                <el-option label="低" value="LOW" />
              </el-select>
            </div>
          </div>

          <div v-if="showAllBulkPanel" class="manual-bulk-panel">
            <div class="manual-bulk-head">
              <div>
                <div class="manual-bulk-title">批量处理</div>
                <div class="manual-bulk-copy">开放任务先推进到今日，已完成任务定期清理。</div>
              </div>
              <el-tag class="mobile-count-tag" size="small" effect="plain">{{ allRows.length }} 条</el-tag>
            </div>
            <div class="manual-bulk-stats">
              <div class="manual-bulk-stat">
                <span>开放</span>
                <strong>{{ openManualCount }}</strong>
              </div>
              <div class="manual-bulk-stat">
                <span>待加入今日</span>
                <strong>{{ allPendingTodayCount }}</strong>
              </div>
              <div class="manual-bulk-stat">
                <span>已完成</span>
                <strong>{{ allDoneRows.length }}</strong>
              </div>
            </div>
            <div class="mobile-toolbar-actions manual-bulk-actions">
              <el-button
                plain
                size="small"
                :icon="Calendar"
                :disabled="allPendingTodayCount <= 0"
                :loading="bulkActionLoading === 'add_today'"
                @click="addAllToToday"
              >
                全部加入今日
              </el-button>
            </div>
          </div>

          <div v-if="activeTab === 'today' && todayRows.length" class="mobile-toolbar-actions">
            <el-button
              plain
              size="small"
              :icon="Files"
              :loading="bulkActionLoading === 'clear_today'"
              @click="clearToday"
            >
              撤销今日列表
            </el-button>
          </div>
        </div>
      </template>

      <div v-loading="showTodoListOverlay" class="mobile-list-stack">
        <template v-if="activeTab === 'system'">
          <div v-if="!activeRows.length" class="mobile-empty-state">
            <div class="mobile-empty-kicker">{{ systemEmptyState.kicker }}</div>
            <div class="mobile-empty-title">{{ systemEmptyState.title }}</div>
            <div class="mobile-empty-copy">{{ systemEmptyState.copy }}</div>
          </div>
          <section v-for="group in systemTodoGroups" :key="group.key" class="system-todo-group">
            <div class="system-todo-group-head">
              <div>
                <div class="system-todo-group-title">{{ group.label }}</div>
                <div class="system-todo-group-copy">{{ group.copy }}</div>
              </div>
              <div class="system-todo-group-side">
                <el-tag class="mobile-count-tag" size="small" effect="plain">{{ group.rows.length }} 条</el-tag>
                <el-button
                  v-if="group.queuePath"
                  class="system-todo-queue-link"
                  text
                  size="small"
                  @click="goTo(group.queuePath)"
                >
                  {{ group.queueLabel }}
                </el-button>
              </div>
            </div>
            <article v-for="row in group.rows" :key="row.id" class="mobile-item-row system-todo-row">
              <div class="mobile-item-main">
                <div class="mobile-item-title-line">
                  <span class="mobile-item-title">{{ row.title }}</span>
                  <el-tag class="mobile-priority-tag" size="small" :type="priorityTagType(row.priority)" effect="plain">
                    {{ priorityLabel(row.priority) }}
                  </el-tag>
                </div>
                <div class="mobile-item-meta">{{ systemTodoMeta(row) }}</div>
                <div v-if="row.description" class="mobile-item-note">{{ row.description }}</div>
              </div>
              <div class="system-todo-actions">
                <div class="system-todo-action-note">{{ systemTodoActionNote(row) }}</div>
                <div class="mobile-item-actions">
                  <el-button class="mobile-primary-action" size="small" type="primary" @click="openSystemAction(row)">
                    {{ systemTodoPrimaryLabel(row) }}
                  </el-button>
                </div>
              </div>
            </article>
          </section>
        </template>

        <template v-else>
          <div v-if="manualFocusOptions.length" class="manual-focus-block">
            <div class="mobile-filter-presets manual-focus-presets">
              <button
                v-for="item in manualFocusOptions"
                :key="`${activeTab}-${item.key}`"
                type="button"
                class="mobile-filter-preset"
                :class="{ active: activeManualFocusKey === item.key }"
                @click="setManualFocus(item.key)"
              >
                <span>{{ item.label }}</span>
                <strong>{{ item.count }}</strong>
              </button>
            </div>
            <div class="manual-focus-hint">{{ manualFocusHint }}</div>
          </div>
          <div v-if="!visibleManualRows.length" class="mobile-empty-state">
            <div class="mobile-empty-kicker">{{ manualEmptyState.kicker }}</div>
            <div class="mobile-empty-title">{{ manualEmptyState.title }}</div>
            <div class="mobile-empty-copy">{{ manualEmptyState.copy }}</div>
          </div>
          <article
            v-for="row in visibleManualRows"
            :key="`${activeTab}-${row.id}`"
            class="mobile-item-row"
            :class="{ done: row.status === 'DONE' }"
          >
            <div class="mobile-item-main">
              <div class="mobile-item-title-line with-checkbox">
                <el-checkbox
                  class="mobile-row-checkbox"
                  :model-value="row.status === 'DONE'"
                  :disabled="actionLoadingTodoId === row.id"
                  @change="(checked: unknown) => toggleTodoDone(row, Boolean(checked))"
                />
                <span class="mobile-item-title">{{ row.title }}</span>
                <el-tag class="mobile-priority-tag" size="small" :type="priorityTagType(row.priority)" effect="plain">
                  {{ priorityLabel(row.priority) }}
                </el-tag>
              </div>
              <div class="mobile-item-meta">{{ todoRowMeta(row) }}</div>
            </div>
            <div class="mobile-item-actions">
              <el-button
                v-if="row.status === 'OPEN' && activeTab === 'today'"
                class="mobile-inline-action"
                text
                size="small"
                :loading="actionLoadingTodoId === row.id"
                @click="toggleTodayMembership(row, false)"
              >
                撤销今日
              </el-button>
              <el-button
                v-else-if="row.status === 'OPEN'"
                class="mobile-inline-action"
                text
                size="small"
                :loading="actionLoadingTodoId === row.id"
                @click="toggleTodayMembership(row, !row.is_in_today)"
              >
                {{ row.is_in_today ? "撤销今日" : "加入今日" }}
              </el-button>
              <el-button
                v-if="canDeleteTodos"
                class="mobile-inline-action"
                text
                size="small"
                type="danger"
                :loading="actionLoadingTodoId === row.id"
                @click="removeTodo(row)"
              >
                删除
              </el-button>
            </div>
          </article>
        </template>
      </div>
    </section>
  </section>
</template>

<style scoped>
.mobile-todo-page {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mobile-hero-block,
.mobile-work-panel {
  border: 1px solid var(--app-border-soft);
  background: rgba(255, 255, 255, 0.88);
  box-shadow: var(--app-shadow-soft);
  padding: 12px;
}

.mobile-section-eyebrow {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--app-text-muted);
}

.mobile-section-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.mobile-section-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.mobile-section-copy {
  margin-top: 2px;
  font-size: 12px;
  line-height: 1.45;
  color: var(--app-text-muted);
}

.todo-skeleton-copy {
  min-width: 0;
  flex: 1;
}

.todo-hero-skeleton-stack {
  margin-top: 10px;
}

.todo-skeleton-focus,
.todo-skeleton-spotlight {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--app-border-soft);
  background: rgba(255, 255, 255, 0.9);
}

.todo-skeleton-focus-side {
  align-items: flex-end;
}

.todo-skeleton-signal,
.todo-skeleton-processing {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 9px;
  border: 1px solid var(--app-border-soft);
  background: var(--app-bg-soft);
}

.todo-skeleton-link {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  padding: 10px;
  border: 1px solid var(--app-border-soft);
  background: rgba(255, 255, 255, 0.9);
}

.todo-skeleton-link-copy,
.todo-skeleton-spotlight-copy,
.todo-skeleton-row-copy {
  min-width: 0;
  flex: 1;
}

.todo-skeleton-segmented {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
}

.todo-skeleton-segmented .mobile-skeleton-button {
  width: 100%;
}

.todo-skeleton-inline-summary {
  flex-wrap: wrap;
  gap: 10px;
}

.todo-skeleton-create-bar,
.todo-skeleton-create-tools {
  display: grid;
  gap: 8px;
}

.todo-skeleton-create-bar {
  grid-template-columns: minmax(0, 1fr) auto;
}

.todo-skeleton-create-tools {
  grid-template-columns: minmax(0, 1fr) 112px;
}

.todo-skeleton-create-bar .mobile-skeleton-line,
.todo-skeleton-create-tools .mobile-skeleton-line {
  height: 32px;
}

.todo-skeleton-list {
  margin-top: 10px;
}

.todo-skeleton-row {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 10px 0;
  border-top: 1px solid var(--app-border-soft);
}

.todo-skeleton-row:first-child {
  border-top: none;
}

.todo-skeleton-checkbox {
  width: 18px;
  height: 18px;
}

.todo-skeleton-row-actions {
  justify-content: flex-end;
}

.mobile-hero-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
}

.mobile-focus-strip {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 10px;
  margin-top: 0;
  padding: 12px;
  border: 1px solid rgba(77, 128, 150, 0.16);
  background:
    linear-gradient(135deg, rgba(77, 128, 150, 0.14), rgba(255, 255, 255, 0.96)),
    var(--app-bg-soft);
}

.mobile-focus-strip.warning {
  border-color: rgba(198, 138, 24, 0.2);
  background: linear-gradient(135deg, rgba(198, 138, 24, 0.14), rgba(255, 255, 255, 0.96));
}

.mobile-focus-strip.danger {
  border-color: rgba(187, 77, 77, 0.22);
  background: linear-gradient(135deg, rgba(187, 77, 77, 0.14), rgba(255, 255, 255, 0.96));
}

.mobile-focus-strip.quiet {
  background: linear-gradient(135deg, rgba(77, 128, 150, 0.08), rgba(255, 255, 255, 0.96));
}

.mobile-focus-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.mobile-focus-label {
  font-size: 11px;
  color: var(--app-text-muted);
}

.mobile-focus-value {
  font-size: 26px;
  line-height: 0.95;
  color: var(--app-text-primary);
}

.mobile-focus-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  font-size: 11px;
  color: var(--app-text-muted);
}

.mobile-focus-action {
  padding-right: 0;
  padding-left: 0;
}

.mobile-signal-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
  margin-top: 0;
}

.mobile-signal-chip {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 8px 9px;
  border: 1px solid var(--app-border-soft);
  background: var(--app-bg-soft);
}

.mobile-signal-chip.accent {
  border-color: rgba(77, 128, 150, 0.22);
  background: rgba(77, 128, 150, 0.1);
}

.mobile-signal-chip.warning {
  border-color: rgba(198, 138, 24, 0.18);
  background: rgba(198, 138, 24, 0.08);
}

.mobile-signal-chip.danger {
  border-color: rgba(187, 77, 77, 0.18);
  background: rgba(187, 77, 77, 0.08);
}

.mobile-signal-chip span {
  font-size: 10px;
  color: var(--app-text-muted);
}

.mobile-signal-chip strong {
  font-size: 13px;
  color: var(--app-text-primary);
}

.mobile-quick-links {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
  margin-top: 0;
}

.mobile-quick-link {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  border: 1px solid var(--app-border-soft);
  background: #fff;
  padding: 10px;
  color: var(--app-text-primary);
}

.mobile-quick-link-icon {
  width: 20px;
  height: 20px;
  display: block;
  color: var(--app-accent-strong);
  flex-shrink: 0;
}

.mobile-quick-link-copy {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.mobile-quick-link-copy span {
  font-size: 11px;
  color: var(--app-text-muted);
}

.mobile-quick-link-copy strong {
  font-size: 15px;
  color: var(--app-text-primary);
}

.mobile-quick-link-copy small {
  font-size: 11px;
  line-height: 1.35;
  color: var(--app-text-muted);
}

.mobile-work-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

:deep(.mobile-count-tag.el-tag) {
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  color: var(--app-text-secondary);
  border-color: rgba(148, 163, 184, 0.22);
  background: rgba(255, 255, 255, 0.82);
}

.mobile-work-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.mobile-processing-strip {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
  margin-top: 0;
}

.mobile-processing-spotlight {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-top: 0;
  padding: 10px;
  border: 1px solid var(--app-border-soft);
  background: rgba(255, 255, 255, 0.92);
}

.mobile-processing-spotlight.accent {
  border-color: rgba(77, 128, 150, 0.2);
  background: linear-gradient(135deg, rgba(77, 128, 150, 0.12), rgba(255, 255, 255, 0.96));
}

.mobile-processing-spotlight.warning {
  border-color: rgba(198, 138, 24, 0.22);
  background: linear-gradient(135deg, rgba(198, 138, 24, 0.12), rgba(255, 255, 255, 0.96));
}

.mobile-processing-spotlight.danger {
  border-color: rgba(187, 77, 77, 0.22);
  background: linear-gradient(135deg, rgba(187, 77, 77, 0.12), rgba(255, 255, 255, 0.96));
}

.mobile-processing-spotlight-main {
  min-width: 0;
  flex: 1;
}

.mobile-processing-spotlight-kicker {
  font-size: 11px;
  color: var(--app-text-muted);
}

.mobile-processing-spotlight-title {
  margin-top: 3px;
  font-size: 13px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.mobile-processing-spotlight-copy {
  margin-top: 3px;
  font-size: 12px;
  line-height: 1.4;
  color: var(--app-text-muted);
}

.mobile-processing-link {
  display: flex;
  flex-direction: column;
  gap: 3px;
  border: 1px solid var(--app-border-soft);
  background: rgba(255, 255, 255, 0.9);
  padding: 10px;
  text-align: left;
  color: var(--app-text-primary);
}

.mobile-processing-link.priority {
  border-color: rgba(77, 128, 150, 0.26);
}

.mobile-processing-link.accent {
  background: rgba(77, 128, 150, 0.08);
}

.mobile-processing-link.warning {
  background: rgba(198, 138, 24, 0.08);
}

.mobile-processing-link.danger {
  background: rgba(187, 77, 77, 0.08);
}

.mobile-processing-link.disabled {
  opacity: 0.52;
}

.mobile-attention-strip {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 0;
}

.mobile-attention-link {
  border: 1px solid var(--app-border-soft);
  background: rgba(255, 255, 255, 0.9);
  padding: 10px;
  text-align: left;
}

.mobile-attention-link.accent {
  background: rgba(77, 128, 150, 0.08);
}

.mobile-attention-link.warning {
  background: rgba(198, 138, 24, 0.08);
}

.mobile-attention-link.danger {
  background: rgba(187, 77, 77, 0.08);
}

.mobile-attention-main {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.mobile-attention-icon {
  width: 18px;
  height: 18px;
  display: block;
  margin-top: 2px;
  color: var(--app-accent-strong);
  flex-shrink: 0;
}

.mobile-attention-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.mobile-attention-copy {
  margin-top: 3px;
  font-size: 12px;
  line-height: 1.4;
  color: var(--app-text-muted);
}

.mobile-processing-main {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.mobile-processing-main span {
  font-size: 11px;
  color: var(--app-text-muted);
}

.mobile-processing-main strong {
  font-size: 13px;
  color: var(--app-text-primary);
}

.mobile-processing-link small {
  font-size: 11px;
  line-height: 1.4;
  color: var(--app-text-muted);
}

.mobile-segmented {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
  margin-top: 0;
}

.mobile-segmented button {
  border: 1px solid var(--app-border-soft);
  background: var(--app-bg-soft);
  color: var(--app-text-muted);
  padding: 9px 8px;
  font-size: 12px;
}

.mobile-segmented button.active {
  border-color: rgba(77, 128, 150, 0.28);
  background: rgba(77, 128, 150, 0.12);
  color: var(--app-accent-strong);
}

.mobile-inline-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  margin-top: 0;
  font-size: 12px;
  color: var(--app-text-muted);
}

.mobile-create-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 0;
  padding-top: 10px;
  border-top: 1px solid var(--app-border-soft);
}

.mobile-create-bar,
.mobile-create-tools {
  display: grid;
  gap: 8px;
}

.mobile-create-bar {
  grid-template-columns: minmax(0, 1fr) auto;
}

.mobile-create-tools {
  grid-template-columns: minmax(0, 1fr) 112px;
}

.mobile-toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 0;
}

.manual-bulk-panel {
  margin-top: 0;
  padding: 10px;
  border: 1px solid var(--app-border-soft);
  background: var(--app-surface-muted);
}

.manual-bulk-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.manual-bulk-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.manual-bulk-copy {
  margin-top: 3px;
  font-size: 12px;
  line-height: 1.4;
  color: var(--app-text-muted);
}

.manual-bulk-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
  margin-top: 8px;
}

.manual-bulk-stat {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 8px 9px;
  border: 1px solid var(--app-border-soft);
  background: rgba(255, 255, 255, 0.85);
}

.manual-bulk-stat span {
  font-size: 11px;
  color: var(--app-text-muted);
}

.manual-bulk-stat strong {
  font-size: 13px;
  color: var(--app-text-primary);
}

.manual-bulk-actions {
  margin-top: 8px;
}

.mobile-list-stack {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 10px;
}

.manual-focus-block {
  margin-top: 2px;
}

.manual-focus-presets {
  margin-top: 0;
}

.manual-focus-hint {
  margin-top: 6px;
  font-size: 11px;
  line-height: 1.4;
  color: var(--app-text-muted);
}

.mobile-item-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 0;
  border-top: 1px solid var(--app-border-soft);
}

.mobile-item-row:first-child {
  border-top: none;
}

.mobile-item-row.done .mobile-item-title {
  color: #94a3b8;
  text-decoration: line-through;
}

.mobile-item-main {
  min-width: 0;
  flex: 1;
}

.mobile-item-title-line {
  display: flex;
  align-items: flex-start;
  gap: 6px;
}

.mobile-item-title-line.with-checkbox {
  align-items: center;
}

:deep(.mobile-row-checkbox.el-checkbox) {
  margin-right: 0;
  flex-shrink: 0;
}

:deep(.mobile-row-checkbox .el-checkbox__inner) {
  width: 16px;
  height: 16px;
  border-radius: 5px;
  border-color: rgba(148, 163, 184, 0.38);
}

:deep(.mobile-row-checkbox .el-checkbox__input.is-checked .el-checkbox__inner) {
  border-color: var(--app-accent-strong);
  background: var(--app-accent-strong);
}

:deep(.mobile-row-checkbox .el-checkbox__input.is-focus .el-checkbox__inner) {
  border-color: rgba(77, 128, 150, 0.46);
}

.mobile-item-title {
  min-width: 0;
  flex: 1;
  font-size: 13px;
  line-height: 1.4;
  color: var(--app-text-primary);
  word-break: break-word;
}

.mobile-item-meta {
  margin-top: 3px;
  font-size: 11px;
  line-height: 1.4;
  color: var(--app-text-muted);
}

.mobile-item-note {
  margin-top: 6px;
  font-size: 11px;
  line-height: 1.45;
  color: var(--app-text-secondary);
}

.mobile-item-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

:deep(.mobile-priority-tag.el-tag) {
  height: 22px;
  padding: 0 7px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.system-todo-group + .system-todo-group {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--app-border-soft);
}

.system-todo-group-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.system-todo-group-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.system-todo-group-copy {
  margin-top: 3px;
  font-size: 11px;
  line-height: 1.4;
  color: var(--app-text-muted);
}

.system-todo-group-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 3px;
}

.system-todo-actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.system-todo-action-note {
  font-size: 11px;
  line-height: 1.4;
  color: var(--app-text-muted);
}

.mobile-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 14px 10px 8px;
  text-align: center;
}

.mobile-empty-kicker {
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--app-text-muted);
}

.mobile-empty-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.mobile-empty-copy {
  max-width: 240px;
  font-size: 11px;
  line-height: 1.45;
  color: var(--app-text-muted);
}

.system-todo-row {
  gap: 6px;
}

:deep(.mobile-primary-action.el-button) {
  min-height: 30px;
  padding: 0 12px;
  border-radius: 10px;
}

:deep(.mobile-inline-action.el-button) {
  min-height: 28px;
  padding: 0 10px;
  border-radius: 9px;
}

:deep(.system-todo-queue-link.el-button) {
  min-height: auto;
  padding: 0;
}

@media (max-width: 420px) {
  .mobile-signal-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .mobile-quick-links {
    grid-template-columns: 1fr;
  }

  .todo-skeleton-create-bar,
  .todo-skeleton-create-tools {
    grid-template-columns: 1fr;
  }

  .mobile-processing-strip {
    grid-template-columns: 1fr;
  }

  .mobile-create-bar,
  .mobile-create-tools {
    grid-template-columns: 1fr;
  }

  .manual-bulk-stats {
    grid-template-columns: 1fr;
  }
}
</style>
