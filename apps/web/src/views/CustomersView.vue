<script setup lang="ts">
import { Filter, MoreFilled } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, ref } from "vue";
import { type LocationQueryRaw, useRoute, useRouter } from "vue-router";

import { apiClient } from "../api/client";
import BillingDraftRowsEditor from "../components/BillingDraftRowsEditor.vue";
import MobileActionSheet from "../components/mobile/MobileActionSheet.vue";
import MobileFilterSheet from "../components/mobile/MobileFilterSheet.vue";
import { useMobileFilterMemory } from "../composables/useMobileFilterMemory";
import { useResponsive } from "../composables/useResponsive";
import { isMobileAppPath } from "../mobile/config";
import { useAuthStore } from "../stores/auth";
import type {
  BillingRecord,
  BillingCreatePayload,
  CustomerDeleteBlockerItem,
  CustomerImportResultItem,
  CustomerListItem,
  CustomerSuggestItem,
} from "../types";
import {
  createEmptyBillingDraft,
  prepareBillingDraftsForSubmit,
  validateBillingDraft,
} from "../utils/billingDraft";
import { getTemplateLabel } from "./lead/viewMeta";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const { isMobile } = useResponsive();
const loading = ref(false);
const customersHydrated = ref(false);
const keyword = ref("");
const rows = ref<CustomerListItem[]>([]);
const showMobileFilters = ref(false);
const expandedCustomerId = ref<number | null>(null);
const showCustomerRowActionSheet = ref(false);
const selectedCustomerActionRow = ref<CustomerListItem | null>(null);
const customerMobileFilterMemory = useMobileFilterMemory("crm.mobile_filters.customers", { keyword: "" });
const canManageGrant = computed(() => auth.user?.role === "OWNER" || auth.user?.role === "ADMIN");
const canDeleteCustomer = computed(() => auth.user?.role === "OWNER" || auth.user?.role === "ADMIN");
const canImportCustomers = computed(
  () => auth.user?.role === "OWNER" || auth.user?.role === "ADMIN" || auth.user?.role === "MANAGER",
);
const canCreateBilling = computed(
  () => auth.user?.role === "OWNER" || auth.user?.role === "ADMIN" || auth.user?.role === "MANAGER",
);
const isMobileWorkflow = computed(() => isMobileAppPath(route.path));
const customerFilterChips = computed(() =>
  keyword.value ? [{ key: "keyword" as const, label: `关键词：${keyword.value}` }] : [],
);
const customerFilterChipLabels = computed(() => customerFilterChips.value.map((item) => item.label));
const showCustomerInitialSkeleton = computed(() => !customersHydrated.value);
const customerRowActionItems = computed(() => {
  const row = selectedCustomerActionRow.value;
  if (!row) return [];
  return [
    { key: "lead", label: "开发来源", description: "回看这位客户的开发来源与线索详情。" },
    canCreateBilling.value
      ? { key: "billing", label: "新增收费项目", description: "直接给当前客户补收费项目。" }
      : null,
    canDeleteCustomer.value
      ? { key: "delete", label: "删除客户", description: "删除前需要输入客户名称确认。", danger: true }
      : null,
  ].filter(Boolean) as Array<{ key: string; label: string; description: string }>;
});
const showCreateBillingDialog = ref(false);
const creatingBilling = ref(false);
const selectedCustomerForBilling = ref<CustomerListItem | null>(null);
const billingRows = ref<BillingCreatePayload[]>([createEmptyBillingDraft(null)]);
const keywordSuggestions = ref<CustomerSuggestItem[]>([]);
const showDeleteCustomerDialog = ref(false);
const deleteBlockers = ref<CustomerDeleteBlockerItem[]>([]);
const deleteTargetCustomer = ref<CustomerListItem | null>(null);
const deleteConfirmValue = ref("");
const deletingCustomer = ref(false);
const importFileInput = ref<HTMLInputElement | null>(null);
const downloadingTemplate = ref(false);
const exportingCustomers = ref(false);
const importingCustomers = ref(false);
const customerSortBy = ref(String(route.query.sort_by || "id"));
const customerSortOrder = ref<"asc" | "desc">(route.query.sort_order === "asc" ? "asc" : "desc");

function mobileMetrics(row: CustomerListItem) {
  return [
    { label: "收费标准", value: row.source_fee_standard || "-" },
    { label: "服务开始", value: row.source_service_start_display || "-" },
    { label: "会计", value: row.accountant_username || "-" },
    { label: "最后跟进", value: row.source_last_followup_date || "未记录" },
  ];
}

function mobileCustomerFacts(row: CustomerListItem) {
  return [
    row.source_area_display ? `地区 ${row.source_area_display}` : "",
    row.source_template_type ? `来源 ${getTemplateLabel(row.source_template_type)}` : "",
    row.source_first_billing_period ? `首单 ${row.source_first_billing_period}` : "",
  ].filter(Boolean);
}

function mobileCustomerBriefs(row: CustomerListItem) {
  return [
    row.source_main_business ? { label: "服务项目", value: row.source_main_business } : null,
    row.source_service_mode ? { label: "服务方式", value: row.source_service_mode } : null,
    row.source_intro ? { label: "介绍人", value: row.source_intro } : null,
  ].filter(Boolean) as Array<{ label: string; value: string }>;
}

async function fetchCustomers() {
  loading.value = true;
  try {
    const resp = await apiClient.get<CustomerListItem[]>("/customers", {
      params: {
        keyword: keyword.value || undefined,
        sort_by: customerSortBy.value || "id",
        sort_order: customerSortOrder.value || "desc",
      },
    });
    rows.value = resp.data;
  } catch (error) {
    ElMessage.error("获取客户列表失败");
  } finally {
    loading.value = false;
    customersHydrated.value = true;
  }
}

function openCustomerDetail(row: CustomerListItem) {
  router.push(`${isMobileWorkflow.value ? "/m/customers" : "/customers"}/${row.id}`);
}

function openLeadDetail(row: CustomerListItem) {
  router.push({
    path: `${isMobileWorkflow.value ? "/m/leads" : "/leads"}/${row.source_lead_id}`,
    query: { from: "customers" },
  });
}

function openGrantSettings() {
  router.push({
    path: isMobileWorkflow.value ? "/m/admin/users" : "/admin/users",
    query: { tab: "grants" },
  });
}

function resetBillingRows(customerId: number | null = null) {
  billingRows.value = [createEmptyBillingDraft(customerId)];
}

function openCreateBillingDialog(row: CustomerListItem) {
  if (!canCreateBilling.value) return;
  resetBillingRows(row.id);
  selectedCustomerForBilling.value = row;
  showCreateBillingDialog.value = true;
}

async function fetchCustomerSuggestions(queryString: string, callback: (items: CustomerSuggestItem[]) => void) {
  const keywordValue = queryString.trim();
  if (!keywordValue) {
    keywordSuggestions.value = [];
    callback([]);
    return;
  }
  try {
    const resp = await apiClient.get<CustomerSuggestItem[]>("/customers/suggest", {
      params: { keyword: keywordValue, limit: 8 },
    });
    keywordSuggestions.value = resp.data;
    callback(resp.data);
  } catch {
    callback([]);
  }
}

function applyKeywordSuggestion(item: CustomerSuggestItem) {
  keyword.value = item.name;
  void fetchCustomers();
}

function openDeleteBlockerTarget(blocker: CustomerDeleteBlockerItem) {
  showDeleteCustomerDialog.value = false;
  if (blocker.filters && Object.keys(blocker.filters).length) {
    const href = blocker.href || "";
    const path = href.split("?")[0] || route.path;
    const query: LocationQueryRaw = {};
    Object.entries(blocker.filters).forEach(([key, value]) => {
      if (typeof value === "string" || typeof value === "number") {
        query[key] = value;
      } else if (value === true) {
        query[key] = "1";
      }
    });
    router.push({
      path,
      query,
    });
    return;
  }
  if (blocker.href) {
    router.push(blocker.href);
  }
}

function customerSortOrderForTable() {
  return customerSortOrder.value === "asc" ? "ascending" : "descending";
}

async function applyCustomerSort(sortBy: string, sortOrder: "asc" | "desc") {
  customerSortBy.value = sortBy;
  customerSortOrder.value = sortOrder;
  await router.replace({
    path: route.path,
    query: {
      ...route.query,
      sort_by: sortBy,
      sort_order: sortOrder,
    },
  });
  await fetchCustomers();
}

async function handleCustomerSortChange(payload: { prop?: string; order: "ascending" | "descending" | null; columnKey?: string }) {
  const sortKey = payload.columnKey || payload.prop || "id";
  const sortOrder = payload.order === "ascending" ? "asc" : "desc";
  await applyCustomerSort(sortKey, sortOrder);
}

function fileNameFromDisposition(disposition: string | undefined, fallback: string) {
  const match = disposition?.match(/filename=\"?([^\";]+)\"?/i);
  return match?.[1] || fallback;
}

function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

async function downloadCustomerTemplate() {
  downloadingTemplate.value = true;
  try {
    const resp = await apiClient.get("/customers/import-template", { responseType: "blob" });
    downloadBlob(
      resp.data,
      fileNameFromDisposition(resp.headers["content-disposition"], "customer-import-template.xlsx"),
    );
    ElMessage.success("客户导入模板已下载");
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "下载客户导入模板失败");
  } finally {
    downloadingTemplate.value = false;
  }
}

async function exportCustomers() {
  exportingCustomers.value = true;
  try {
    const resp = await apiClient.get("/customers/export", {
      params: {
        keyword: keyword.value || undefined,
      },
      responseType: "blob",
    });
    downloadBlob(
      resp.data,
      fileNameFromDisposition(resp.headers["content-disposition"], "customers-export.xlsx"),
    );
    ElMessage.success("客户列表已导出");
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "导出客户列表失败");
  } finally {
    exportingCustomers.value = false;
  }
}

function triggerCustomerImport() {
  importFileInput.value?.click();
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function buildImportSummaryHtml(result: CustomerImportResultItem) {
  const lines = [
    `新增：${result.created_count}`,
    `更新：${result.updated_count}`,
    `跳过：${result.skipped_count}`,
    `错误：${result.error_count}`,
  ];
  const errorRows = result.rows.filter((item) => item.action === "ERROR").slice(0, 12);
  const errorHtml = errorRows.length
    ? `<br/><br/><strong>出错行：</strong><br/>${errorRows
        .map((item) => `第 ${item.row_number} 行 · ${escapeHtml(item.company_name)} · ${escapeHtml(item.message)}`)
        .join("<br/>")}`
    : "";
  return `<div style="white-space:pre-wrap;line-height:1.7;">${lines.join("<br/>")}${errorHtml}</div>`;
}

async function handleCustomerImportChange(event: Event) {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  target.value = "";
  if (!file) return;

  importingCustomers.value = true;
  try {
    const formData = new FormData();
    formData.append("file", file);
    const resp = await apiClient.post<CustomerImportResultItem>("/customers/import", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    await fetchCustomers();
    await ElMessageBox.alert(buildImportSummaryHtml(resp.data), "客户导入结果", {
      dangerouslyUseHTMLString: true,
      confirmButtonText: "知道了",
    });
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "导入客户列表失败");
  } finally {
    importingCustomers.value = false;
  }
}

function openDeleteCustomerDialog(row: CustomerListItem) {
  deleteTargetCustomer.value = row;
  deleteConfirmValue.value = "";
  deleteBlockers.value = [];
  showDeleteCustomerDialog.value = true;
}

async function submitDeleteCustomer() {
  const row = deleteTargetCustomer.value;
  if (!row) return;
  if (!canDeleteCustomer.value) {
    ElMessage.warning("只有老板和管理员可以删除客户");
    return;
  }
  const expectedName = (row.name || "").trim() || (row.contact_name || "").trim() || `客户#${row.id}`;
  if ((deleteConfirmValue.value || "").trim() !== expectedName) {
    ElMessage.warning("请输入完整客户名称后再确认删除");
    return;
  }
  deletingCustomer.value = true;
  try {
    await apiClient.delete(`/customers/${row.id}`, {
      params: { confirm_name: expectedName },
    });
    showDeleteCustomerDialog.value = false;
    deleteTargetCustomer.value = null;
    deleteConfirmValue.value = "";
    deleteBlockers.value = [];
    ElMessage.success("客户已删除");
    await fetchCustomers();
  } catch (error: any) {
    const detail = error?.response?.data?.detail;
    if (detail?.reason === "DEPENDENCY_BLOCKED" && Array.isArray(detail.blockers)) {
      deleteBlockers.value = detail.blockers;
      return;
    }
    ElMessage.error(detail ?? "删除客户失败");
  } finally {
    deletingCustomer.value = false;
  }
}

function handleMobileCommand(command: string, row: CustomerListItem) {
  if (command === "detail") openCustomerDetail(row);
  if (command === "billing") openCreateBillingDialog(row);
  if (command === "lead") openLeadDetail(row);
  if (command === "delete") openDeleteCustomerDialog(row);
}

function onMobileMenuCommand(command: { action: string; row: CustomerListItem }) {
  handleMobileCommand(command.action, command.row);
}

function openCustomerRowActions(row: CustomerListItem) {
  selectedCustomerActionRow.value = row;
  showCustomerRowActionSheet.value = true;
}

function handleCustomerRowActionSelect(action: string) {
  if (!selectedCustomerActionRow.value) return;
  handleMobileCommand(action, selectedCustomerActionRow.value);
}

function resetKeywordAndQuery() {
  keyword.value = "";
  customerMobileFilterMemory.clearState();
  void fetchCustomers();
}

function toggleExpandedCustomer(customerId: number) {
  expandedCustomerId.value = expandedCustomerId.value === customerId ? null : customerId;
}

function restoreSavedCustomerFilters() {
  customerMobileFilterMemory.restoreSavedState((snapshot) => {
    keyword.value = snapshot.keyword;
  });
}

async function applyCustomerFilters() {
  if (isMobileWorkflow.value) {
    customerMobileFilterMemory.saveState({ keyword: keyword.value });
  }
  await fetchCustomers();
}

function handleCreateBillingDialogClosed() {
  resetBillingRows();
  selectedCustomerForBilling.value = null;
}

async function createBillingRecordForCustomer() {
  const validationError = billingRows.value
    .map((item, index) => validateBillingDraft(item, index))
    .find((item) => item);
  if (validationError) {
    ElMessage.warning(validationError);
    return;
  }
  creatingBilling.value = true;
  try {
    const payload = prepareBillingDraftsForSubmit(billingRows.value);
    const resp = await apiClient.post<BillingRecord[]>("/billing-records/batch", { records: payload });
    showCreateBillingDialog.value = false;
    ElMessage.success(`已创建 ${resp.data.length} 条收费项目`);
    resetBillingRows();
    const targetCustomer = selectedCustomerForBilling.value;
    selectedCustomerForBilling.value = null;
    if (targetCustomer) {
      try {
        await ElMessageBox.confirm(
          "收费项目已保存。接下来可以继续补收费项目，或立即登记这位客户的收款单。",
          "下一步",
          {
            confirmButtonText: "立即登记收款",
            cancelButtonText: "继续新增收费项目",
            distinguishCancelAndClose: true,
            type: "success",
          },
        );
        router.push(`/billing?view=payments&customer_id=${targetCustomer.id}&open_payment=1`);
      } catch (nextAction) {
        if (nextAction === "cancel") {
          openCreateBillingDialog(targetCustomer);
        }
      }
    }
  } catch (error) {
    ElMessage.error("创建收费项目失败");
  } finally {
    creatingBilling.value = false;
  }
}

onMounted(async () => {
  customerSortBy.value = String(route.query.sort_by || "id");
  customerSortOrder.value = route.query.sort_order === "asc" ? "asc" : "desc";
  if (isMobileWorkflow.value) {
    restoreSavedCustomerFilters();
  }
  await fetchCustomers();
});
</script>

<template>
  <template v-if="isMobileWorkflow">
    <section class="mobile-page customer-mobile-page">
      <section class="mobile-shell-panel">
        <div class="mobile-toolbar">
          <div class="mobile-toolbar-main">
            <el-autocomplete
              v-model="keyword"
              :fetch-suggestions="fetchCustomerSuggestions"
              placeholder="客户 / 联系人 / 电话 / 会计"
              clearable
              @select="applyKeywordSuggestion"
              @keyup.enter="applyCustomerFilters"
            />
          </div>
          <div class="mobile-toolbar-actions">
            <el-button class="mobile-row-secondary-button" plain :icon="Filter" @click="showMobileFilters = true">
              筛选
            </el-button>
            <el-button v-if="canManageGrant" class="mobile-row-secondary-button" plain @click="openGrantSettings">
              授权
            </el-button>
          </div>
        </div>
        <div v-if="keyword" class="mobile-chip-row customer-mobile-chip-row">
          <button type="button" class="mobile-chip-button" @click="resetKeywordAndQuery">
            <span>关键词：{{ keyword }}</span>
            <span class="mobile-chip-close">移除</span>
          </button>
          <button type="button" class="customer-clear-chip" @click="resetKeywordAndQuery">清空</button>
        </div>
      </section>

      <section class="mobile-shell-panel customer-mobile-list-panel">
        <div class="head">
          <div>
            <div class="card-title">客户列表</div>
            <div class="card-subtitle">先看客户，再直接进档案、补收费或回看来源。</div>
          </div>
          <div v-if="showCustomerInitialSkeleton" class="mobile-skeleton-chip customer-mobile-count-skeleton"></div>
          <el-tag v-else class="mobile-count-tag" effect="plain">{{ rows.length }} 条</el-tag>
        </div>

        <div v-loading="loading && customersHydrated" class="customer-mobile-list">
          <template v-if="showCustomerInitialSkeleton">
            <article
              v-for="index in 4"
              :key="`customer-skeleton-${index}`"
              class="customer-mobile-row customer-mobile-skeleton-row"
            >
              <div class="customer-mobile-row-top">
                <div class="mobile-skeleton-line is-lg"></div>
                <div class="mobile-skeleton-chip"></div>
              </div>
              <div class="mobile-skeleton-stack">
                <div class="mobile-skeleton-line is-md"></div>
                <div class="mobile-skeleton-line is-xl"></div>
              </div>
              <div class="customer-mobile-skeleton-metrics">
                <div v-for="metricIndex in 4" :key="`customer-skeleton-metric-${index}-${metricIndex}`" class="customer-mobile-skeleton-metric">
                  <div class="mobile-skeleton-line is-xs"></div>
                  <div class="mobile-skeleton-line is-sm"></div>
                </div>
              </div>
              <div class="customer-mobile-skeleton-actions">
                <div class="mobile-skeleton-button"></div>
                <div class="mobile-skeleton-button"></div>
              </div>
            </article>
          </template>
          <div v-else-if="!rows.length" class="mobile-empty-block">
            <div class="mobile-empty-kicker">客户列表</div>
            <div class="mobile-empty-title">当前没有匹配的客户</div>
            <div class="mobile-empty-copy">换个关键词再查，或回到开发列表继续推进新增客户。</div>
          </div>
          <article v-for="row in rows" :key="row.id" class="customer-mobile-row">
            <div class="customer-mobile-row-top">
              <button type="button" class="customer-mobile-name" @click="openCustomerDetail(row)">{{ row.name }}</button>
              <el-tag class="mobile-status-tag" size="small" effect="plain">
                {{ row.accountant_username || "未分配会计" }}
              </el-tag>
            </div>
            <div class="customer-mobile-summary">{{ row.contact_name || "-" }} / {{ row.phone || "-" }}</div>
            <div class="customer-mobile-meta">
              {{ [row.source_service_start_display, row.source_fee_standard, row.source_last_followup_date ? `最后跟进 ${row.source_last_followup_date}` : ""].filter(Boolean).join(" · ") || "暂无补充信息" }}
            </div>

            <transition name="customer-expand">
              <div v-if="expandedCustomerId === row.id" class="customer-mobile-expanded">
                <div class="customer-mobile-extra-grid">
                  <div v-for="item in mobileMetrics(row)" :key="`${row.id}-${item.label}`" class="customer-mobile-extra-item">
                    <span>{{ item.label }}</span>
                    <strong>{{ item.value }}</strong>
                  </div>
                </div>
                <div v-if="mobileCustomerFacts(row).length" class="customer-mobile-fact-row">
                  <span
                    v-for="fact in mobileCustomerFacts(row)"
                    :key="`${row.id}-${fact}`"
                    class="customer-mobile-fact-chip"
                  >
                    {{ fact }}
                  </span>
                </div>
                <div v-if="mobileCustomerBriefs(row).length" class="customer-mobile-brief-list">
                  <div
                    v-for="item in mobileCustomerBriefs(row)"
                    :key="`${row.id}-${item.label}`"
                    class="customer-mobile-brief"
                  >
                    <span>{{ item.label }}</span>
                    <strong>{{ item.value }}</strong>
                  </div>
                </div>
              </div>
            </transition>

            <div class="mobile-action-stack customer-mobile-actions">
              <div class="mobile-action-main">
                <el-button class="mobile-row-primary-button" size="small" type="primary" @click="openCustomerDetail(row)">
                  客户档案
                </el-button>
                <el-button
                  v-if="canCreateBilling"
                  class="mobile-row-secondary-button"
                  size="small"
                  plain
                  @click="openCreateBillingDialog(row)"
                >
                  新增收费项目
                </el-button>
                <el-button
                  v-else
                  class="mobile-row-secondary-button"
                  size="small"
                  plain
                  @click="openLeadDetail(row)"
                >
                  开发来源
                </el-button>
              </div>
              <div class="mobile-action-sub">
                <button v-if="canCreateBilling" type="button" class="mobile-action-link" @click="openLeadDetail(row)">
                  开发来源
                </button>
                <button type="button" class="mobile-action-link is-muted" @click="toggleExpandedCustomer(row.id)">
                  {{ expandedCustomerId === row.id ? "收起补充信息" : "展开补充信息" }}
                </button>
                <button type="button" class="mobile-action-link" @click="openCustomerRowActions(row)">更多操作</button>
              </div>
            </div>
          </article>
        </div>
      </section>
    </section>

    <MobileFilterSheet
      v-model="showMobileFilters"
      title="筛选客户"
      subtitle="先确定要看的客户范围，再继续维护。"
      :summary-items="customerFilterChipLabels"
      empty-summary="当前未设置筛选条件"
    >
      <el-form label-position="top" class="customer-mobile-filter-form">
        <div v-if="customerMobileFilterMemory.hasSavedState.value" class="mobile-filter-restore">
          <el-button text type="primary" @click="restoreSavedCustomerFilters">恢复上次已应用条件</el-button>
        </div>
        <el-form-item label="关键词">
          <el-autocomplete
            v-model="keyword"
            :fetch-suggestions="fetchCustomerSuggestions"
            placeholder="客户 / 联系人 / 电话 / 会计"
            clearable
            @select="applyKeywordSuggestion"
            @keyup.enter="applyCustomerFilters"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetKeywordAndQuery">重置</el-button>
        <el-button type="primary" @click="showMobileFilters = false; applyCustomerFilters()">应用筛选</el-button>
      </template>
    </MobileFilterSheet>

    <MobileActionSheet
      v-model="showCustomerRowActionSheet"
      title="客户操作"
      :subtitle="selectedCustomerActionRow?.name || ''"
      :items="customerRowActionItems"
      @select="handleCustomerRowActionSelect"
    />
  </template>

  <el-space v-else direction="vertical" fill :size="10" class="workspace-page">
    <section class="workspace-header">
      <div class="workspace-title-block">
        <div class="workspace-title">客户列表</div>
        <div class="workspace-copy">先看客户，再直接进档案、补收费或回看来源。</div>
      </div>
      <div class="workspace-actions">
        <el-tag type="success" effect="plain" class="workspace-subtle-tag">{{ rows.length }} 条</el-tag>
      </div>
    </section>

    <el-card shadow="never" class="workspace-surface">
      <div class="workspace-inline-toolbar">
        <div class="workspace-inline-toolbar-main">
          <el-form inline @submit.prevent="fetchCustomers" class="customers-filter-form">
        <el-form-item label="关键词">
          <el-autocomplete
            v-model="keyword"
            :fetch-suggestions="fetchCustomerSuggestions"
            placeholder="客户/联系人/电话/会计"
            clearable
            @select="applyKeywordSuggestion"
            @keyup.enter="fetchCustomers"
          />
        </el-form-item>
        <el-form-item>
          <el-button @click="fetchCustomers">查询</el-button>
          <el-button plain :loading="downloadingTemplate" @click="downloadCustomerTemplate">下载导入模板</el-button>
          <el-button plain :loading="exportingCustomers" @click="exportCustomers">导出客户</el-button>
          <el-button v-if="canImportCustomers" type="primary" plain :loading="importingCustomers" @click="triggerCustomerImport">
            导入客户
          </el-button>
          <el-button v-if="canManageGrant" type="primary" plain @click="openGrantSettings">数据授权配置</el-button>
        </el-form-item>
          </el-form>
        </div>
      </div>
    </el-card>

    <el-card shadow="never" class="workspace-surface">
      <template #header>
        <div class="head">
          <div>
            <div class="card-title">已成交客户</div>
            <div class="card-subtitle">转给会计或经办人后在这里继续维护。</div>
          </div>
          <el-tag type="success" effect="plain" class="workspace-subtle-tag">{{ rows.length }} 条</el-tag>
        </div>
      </template>
      <div v-if="isMobile" v-loading="loading" class="mobile-record-list">
        <div v-for="row in rows" :key="row.id" class="mobile-record-card">
          <div class="mobile-record-head">
            <div class="mobile-record-main">
              <el-button link type="primary" class="mobile-record-title" @click="openCustomerDetail(row)">
                {{ row.name }}
              </el-button>
              <div class="mobile-record-subtitle">
                {{ row.contact_name || "-" }} / {{ row.phone || "-" }}
              </div>
            </div>
            <el-tag size="small" effect="plain">{{ row.responsible_username || row.accountant_username || "-" }}</el-tag>
          </div>

          <div class="mobile-record-metrics">
            <div v-for="item in mobileMetrics(row)" :key="`${row.id}-${item.label}`" class="mobile-metric">
              <div class="mobile-metric-label">{{ item.label }}</div>
              <div class="mobile-metric-value">{{ item.value }}</div>
            </div>
          </div>

          <div v-if="row.source_main_business || row.source_intro" class="mobile-record-note">
            <div v-if="row.source_main_business">主营：{{ row.source_main_business }}</div>
            <div v-if="row.source_intro">介绍人：{{ row.source_intro }}</div>
          </div>

          <div class="mobile-actions">
            <el-button size="small" type="primary" @click="openCustomerDetail(row)">客户档案</el-button>
            <el-button v-if="canCreateBilling" size="small" type="success" plain @click="openCreateBillingDialog(row)">
              新增收费项目
            </el-button>
            <el-dropdown trigger="click" @command="onMobileMenuCommand">
              <el-button size="small" plain>
                更多
                <el-icon><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item :command="{ action: 'lead', row }">开发来源</el-dropdown-item>
                  <el-dropdown-item v-if="canCreateBilling" :command="{ action: 'billing', row }">新增收费项目</el-dropdown-item>
                  <el-dropdown-item v-if="canDeleteCustomer" :command="{ action: 'delete', row }">删除客户</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>
      <el-table
        v-else
        v-loading="loading"
        :data="rows"
        stripe
        border
        size="small"
        class="customer-table-compact"
        :default-sort="{ prop: customerSortBy, order: customerSortOrderForTable() }"
        @sort-change="handleCustomerSortChange"
      >
        <el-table-column prop="id" label="序号" width="80" sortable="custom" />
        <el-table-column label="客户号+公司名" min-width="180" show-overflow-tooltip column-key="name" sortable="custom">
          <template #default="{ row }">
            <div class="customer-name-cell">
              <el-tag v-if="row.customer_code" size="small" effect="plain">{{ row.customer_code }}</el-tag>
              <el-button link type="primary" @click="openCustomerDetail(row)">{{ row.name }}</el-button>
            </div>
          </template>
        </el-table-column>
        <el-table-column
          prop="source_fee_standard"
          label="收费标准"
          min-width="130"
          show-overflow-tooltip
        />
        <el-table-column
          prop="source_main_business"
          label="服务项目/主营"
          min-width="180"
          show-overflow-tooltip
        />
        <el-table-column
          prop="source_grade"
          label="等级"
          width="110"
          show-overflow-tooltip
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="source_service_start_display"
          label="服务开始"
          width="110"
          column-key="created_at"
          sortable="custom"
        />
        <el-table-column
          prop="contact_name"
          label="对接人及电话"
          min-width="160"
          sortable="custom"
        >
          <template #default="{ row }">{{ `${row.contact_name || "-"} / ${row.phone || "-"}` }}</template>
        </el-table-column>
        <el-table-column
          prop="source_last_followup_date"
          label="最后跟进"
          width="110"
        />
        <el-table-column
          prop="accountant_username"
          label="负责人/会计"
          width="128"
          column-key="accountant"
          sortable="custom"
        >
          <template #default="{ row }">
            {{ row.responsible_username || row.accountant_username || "-" }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-space class="table-action-wrap">
              <el-button link type="primary" @click="openCustomerDetail(row)">客户档案</el-button>
              <el-button v-if="canCreateBilling" link type="success" @click="openCreateBillingDialog(row)">
                新增收费项目
              </el-button>
              <el-button link @click="openLeadDetail(row)">开发来源</el-button>
              <el-button v-if="canDeleteCustomer" link type="danger" @click="openDeleteCustomerDialog(row)">删除</el-button>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </el-space>

  <el-dialog
    v-model="showCreateBillingDialog"
    title="新增收费项目"
    :width="isMobileWorkflow ? '94%' : '760px'"
    @closed="handleCreateBillingDialogClosed"
  >
    <el-form label-position="top">
      <el-form-item label="客户">
        <el-input
          :model-value="selectedCustomerForBilling ? `${selectedCustomerForBilling.name}（${selectedCustomerForBilling.contact_name}）` : ''"
          disabled
        />
      </el-form-item>
      <el-text type="info" size="small">
        同一客户可以连续增行多个收费项目，统一保存。按期项目填写开始月份即可默认生成 12 个月合同；按次项目再填写实际日期。
      </el-text>
    </el-form>
    <BillingDraftRowsEditor v-model="billingRows" title-prefix="收费明细" />
    <template #footer>
      <el-button @click="showCreateBillingDialog = false">取消</el-button>
      <el-button type="primary" :loading="creatingBilling" @click="createBillingRecordForCustomer">
        保存 {{ billingRows.length }} 条
      </el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="showDeleteCustomerDialog" title="删除客户" width="620px" align-center destroy-on-close>
    <template v-if="!deleteBlockers.length">
      <div class="customer-delete-blockers-copy">
        请输入完整客户名称确认删除：
        <strong>{{ deleteTargetCustomer?.name || "该客户" }}</strong>
      </div>
      <el-input
        v-model="deleteConfirmValue"
        :placeholder="deleteTargetCustomer?.name || '请输入完整客户名称'"
        class="customer-delete-input"
        @keyup.enter="submitDeleteCustomer"
      />
    </template>
    <template v-else>
      <div class="customer-delete-blockers-copy">
        <strong>{{ deleteTargetCustomer?.name || "该客户" }}</strong>
        还有关联记录。先处理下面这些内容，再回来删除客户会更安全。
      </div>
      <div class="customer-delete-blockers">
        <article v-for="item in deleteBlockers" :key="`${item.type}-${item.href}`" class="customer-delete-blocker-card">
          <div class="customer-delete-blocker-main">
            <div class="customer-delete-blocker-title">{{ item.label }}<span> · {{ item.count }} 条</span></div>
            <div class="customer-delete-blocker-text">{{ item.message }}</div>
          </div>
          <el-button type="primary" plain size="small" @click="openDeleteBlockerTarget(item)">去处理</el-button>
        </article>
      </div>
    </template>
    <template #footer>
      <el-button @click="showDeleteCustomerDialog = false">取消</el-button>
      <el-button
        v-if="!deleteBlockers.length"
        type="danger"
        :loading="deletingCustomer"
        @click="submitDeleteCustomer"
      >
        确认删除
      </el-button>
      <el-button v-else type="primary" @click="showDeleteCustomerDialog = false">知道了</el-button>
    </template>
  </el-dialog>

  <input
    ref="importFileInput"
    type="file"
    accept=".xlsx,.csv"
    style="display: none"
    @change="handleCustomerImportChange"
  />
</template>

<style scoped>
.customer-mobile-page {
  gap: 12px;
}

.customer-mobile-chip-row {
  margin-top: 12px;
}

.customer-clear-chip {
  border: none;
  background: transparent;
  padding: 0;
  color: var(--app-accent-strong);
  font-size: 12px;
}

.customer-mobile-list-panel {
  padding-top: 12px;
}

.customer-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.customer-table-compact :deep(.el-table__cell) {
  padding: 4px 0;
}

.customer-delete-input {
  margin-top: 14px;
}

.customer-delete-blockers-copy {
  font-size: 14px;
  line-height: 1.7;
  color: var(--app-text-secondary);
}

.customer-delete-blockers {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 14px;
}

.customer-delete-blocker-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  border: 1px solid var(--app-border-soft);
  background: var(--app-surface);
}

.customer-delete-blocker-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.customer-delete-blocker-title span {
  font-weight: 500;
  color: var(--app-text-muted);
}

.customer-delete-blocker-text {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--app-text-muted);
}

.customer-mobile-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 14px;
}

.customer-mobile-count-skeleton {
  flex-shrink: 0;
}

.customer-mobile-row {
  border-top: 1px solid var(--app-border-soft);
  padding-top: 12px;
}

.customer-mobile-row:first-child {
  border-top: none;
  padding-top: 0;
}

.customer-mobile-row-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.customer-mobile-skeleton-row {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.customer-mobile-skeleton-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.customer-mobile-skeleton-metric {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px;
  border: 1px solid var(--app-border-soft);
  border-radius: 14px;
  background: color-mix(in srgb, var(--app-bg-soft) 70%, white 30%);
}

.customer-mobile-skeleton-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.customer-mobile-name {
  border: none;
  padding: 0;
  background: transparent;
  text-align: left;
  font-size: 15px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.customer-mobile-summary {
  margin-top: 6px;
  font-size: 13px;
  color: var(--app-text-secondary);
}

.customer-mobile-meta {
  margin-top: 4px;
  font-size: 12px;
  color: var(--app-text-muted);
}

.customer-mobile-expanded {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--app-border-soft);
}

.customer-mobile-extra-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.customer-mobile-extra-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  background: color-mix(in srgb, var(--app-bg-soft) 70%, white 30%);
  border: 1px solid var(--app-border-soft);
  border-radius: 14px;
}

.customer-mobile-extra-item span {
  font-size: 11px;
  color: var(--app-text-muted);
}

.customer-mobile-extra-item strong {
  font-size: 13px;
  line-height: 1.4;
  color: var(--app-text-primary);
}

.customer-mobile-fact-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.customer-mobile-fact-chip {
  padding: 5px 10px;
  border-radius: 999px;
  background: var(--app-bg-soft);
  font-size: 11px;
  color: var(--app-text-muted);
}

.customer-mobile-brief-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
}

.customer-mobile-brief {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 8px;
  font-size: 12px;
  line-height: 1.55;
}

.customer-mobile-brief span {
  color: var(--app-text-muted);
}

.customer-mobile-brief strong {
  font-size: 12px;
  font-weight: 500;
  color: var(--app-text-secondary);
  word-break: break-word;
}

.customer-mobile-actions {
  margin-top: 12px;
}

.customer-mobile-filter-form :deep(.el-form-item) {
  margin-bottom: 14px;
}

.mobile-filter-restore {
  display: flex;
  justify-content: flex-start;
  margin-bottom: 6px;
}

.customer-expand-enter-active,
.customer-expand-leave-active {
  transition: opacity 180ms ease, transform 180ms ease;
}

.customer-expand-enter-from,
.customer-expand-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px 16px;
}

.card-title {
  font-size: 15px;
  font-weight: 700;
  color: #111827;
}

.card-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
}

.customers-filter-form :deep(.el-form-item) {
  margin-bottom: 0;
}

@media (max-width: 768px) {
  .customers-filter-form {
    display: flex;
    flex-wrap: wrap;
  }

  .mobile-actions :deep(.el-button) {
    margin-left: 0;
  }
}

@media (max-width: 420px) {
  .customer-mobile-skeleton-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
