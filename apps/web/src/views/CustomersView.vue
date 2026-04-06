<script setup lang="ts">
import { Filter, MoreFilled } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { apiClient } from "../api/client";
import BillingDraftRowsEditor from "../components/BillingDraftRowsEditor.vue";
import MobileActionSheet from "../components/mobile/MobileActionSheet.vue";
import MobileFilterSheet from "../components/mobile/MobileFilterSheet.vue";
import { useMobileFilterMemory } from "../composables/useMobileFilterMemory";
import { useResponsive } from "../composables/useResponsive";
import { isMobileAppPath } from "../mobile/config";
import { useAuthStore } from "../stores/auth";
import type { BillingRecord, BillingCreatePayload, CustomerListItem } from "../types";
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
      ? { key: "billing", label: "新增收费", description: "直接给当前客户补收费单。" }
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

async function removeCustomer(row: CustomerListItem) {
  if (!canDeleteCustomer.value) {
    ElMessage.warning("只有老板和管理员可以删除客户");
    return;
  }
  const expectedName = (row.name || "").trim() || (row.contact_name || "").trim() || `客户#${row.id}`;
  try {
    const result = (await ElMessageBox.prompt(
      `请输入“${expectedName}”确认删除这位客户。`,
      "删除客户",
      {
        type: "warning",
        confirmButtonText: "确认删除",
        cancelButtonText: "取消",
        inputPlaceholder: expectedName,
      },
    )) as { value: string };
    if ((result.value || "").trim() !== expectedName) {
      ElMessage.warning("输入名称不一致，已取消删除");
      return;
    }
    await apiClient.delete(`/customers/${row.id}`, {
      params: { confirm_name: expectedName },
    });
    ElMessage.success("客户已删除");
    await fetchCustomers();
  } catch (error: any) {
    if (error === "cancel" || error?.message === "cancel") return;
    ElMessage.error(error?.response?.data?.detail ?? "删除客户失败");
  }
}

function handleMobileCommand(command: string, row: CustomerListItem) {
  if (command === "detail") openCustomerDetail(row);
  if (command === "billing") openCreateBillingDialog(row);
  if (command === "lead") openLeadDetail(row);
  if (command === "delete") void removeCustomer(row);
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
    ElMessage.success(`已创建 ${resp.data.length} 条收费记录`);
    resetBillingRows();
    selectedCustomerForBilling.value = null;
  } catch (error) {
    ElMessage.error("创建收费记录失败");
  } finally {
    creatingBilling.value = false;
  }
}

onMounted(async () => {
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
            <el-input
              v-model="keyword"
              placeholder="客户 / 联系人 / 电话 / 会计"
              clearable
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
                  新增收费
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
          <el-input
            v-model="keyword"
            placeholder="客户 / 联系人 / 电话 / 会计"
            clearable
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

  <el-space v-else direction="vertical" fill :size="12">
    <el-card shadow="never">
      <el-form inline @submit.prevent="fetchCustomers" class="customers-filter-form">
        <el-form-item label="关键词">
          <el-input
            v-model="keyword"
            placeholder="客户/联系人/电话/会计"
            clearable
            @keyup.enter="fetchCustomers"
          />
        </el-form-item>
        <el-form-item>
          <el-button @click="fetchCustomers">查询</el-button>
          <el-button v-if="canManageGrant" type="primary" plain @click="openGrantSettings">数据授权配置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="head">
          <div>
            <div class="card-title">客户列表</div>
            <div class="card-subtitle">这里只显示已成交客户，转给会计或经办人后在这里继续维护。</div>
          </div>
          <el-tag type="success" effect="plain">{{ rows.length }} 条</el-tag>
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
            <el-tag size="small" effect="plain">{{ row.accountant_username || "-" }}</el-tag>
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
              新增收费
            </el-button>
            <el-dropdown trigger="click" @command="onMobileMenuCommand">
              <el-button size="small" plain>
                更多
                <el-icon><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item :command="{ action: 'lead', row }">开发来源</el-dropdown-item>
                  <el-dropdown-item v-if="canCreateBilling" :command="{ action: 'billing', row }">新增收费</el-dropdown-item>
                  <el-dropdown-item v-if="canDeleteCustomer" :command="{ action: 'delete', row }">删除客户</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>
      <el-table v-else v-loading="loading" :data="rows" stripe border>
        <el-table-column prop="id" label="序号" width="80" />
        <el-table-column label="客户号+公司名" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <el-button link type="primary" @click="openCustomerDetail(row)">{{ row.name }}</el-button>
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
        />
        <el-table-column
          prop="contact_name"
          label="对接人及电话"
          min-width="160"
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
          label="会计"
          width="110"
        />
        <el-table-column
          label="操作"
          width="200"
        >
          <template #default="{ row }">
            <el-space class="table-action-wrap">
              <el-button link type="primary" @click="openCustomerDetail(row)">客户档案</el-button>
              <el-button v-if="canCreateBilling" link type="success" @click="openCreateBillingDialog(row)">
                新增收费
              </el-button>
              <el-button link @click="openLeadDetail(row)">开发来源</el-button>
              <el-button v-if="canDeleteCustomer" link type="danger" @click="removeCustomer(row)">删除</el-button>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </el-space>

  <el-dialog
    v-model="showCreateBillingDialog"
    title="新增收费记录"
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
  align-items: center;
  gap: 16px;
}

.card-title {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}

.card-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
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
