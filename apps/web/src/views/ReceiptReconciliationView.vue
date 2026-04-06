<script setup lang="ts">
import { Filter } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

import { apiClient } from "../api/client";
import MobileFilterSheet from "../components/mobile/MobileFilterSheet.vue";
import { useResponsive } from "../composables/useResponsive";
import { isMobileAppPath } from "../mobile/config";
import { useAuthStore } from "../stores/auth";
import type { BillingReceiptAccountLedgerData } from "../types";
import { addDaysToDateString, todayInBrowserTimeZone } from "../utils/time";
import { getMonthDateRange, receiptAccountOptions } from "./billing/viewMeta";

const route = useRoute();
const auth = useAuthStore();
const { isMobile } = useResponsive();

const loading = ref(false);
const receiptHydrated = ref(false);
const receiptAccount = ref("");
const dateRange = ref<[string, string] | null>(null);
const data = ref<BillingReceiptAccountLedgerData | null>(null);
const showMobileFilters = ref(false);
const isMobileWorkflow = computed(() => isMobileAppPath(route.path));
type ReceiptDatePreset = "LAST_7_DAYS" | "LAST_30_DAYS" | "THIS_MONTH" | "LAST_MONTH";
const receiptDatePreset = ref<ReceiptDatePreset | "">("");

const accountOptions = computed(() => {
  const dynamicOptions = (data.value?.account_summaries || []).map((item) => ({
    value: item.receipt_account,
    label: item.receipt_account,
  }));
  const merged = new Map<string, string>();
  [...receiptAccountOptions, ...dynamicOptions].forEach((item) => {
    const value = (item.value || "").trim();
    if (value) {
      merged.set(value, item.label);
    }
  });
  return Array.from(merged.entries()).map(([value, label]) => ({ value, label }));
});

const scopeLabel = computed(() => {
  if (auth.user?.role === "MANAGER") return "当前范围：直属下属";
  if (auth.user?.role === "ADMIN") return "当前范围：管理员可见";
  if (auth.user?.role === "ACCOUNTANT") return "当前范围：收费授权";
  return "当前范围：全公司";
});

const selectedAccountLabel = computed(() => receiptAccount.value || "全部账户");
const visibleEntries = computed(() => data.value?.entries || []);
const showReceiptInitialSkeleton = computed(() => !receiptHydrated.value);
const mobileAccountPresets = computed(() => {
  const items = data.value?.account_summaries || [];
  return [
    {
      key: "",
      label: "全部账户",
      meta: `${data.value?.payment_count ?? 0} 笔`,
      total: data.value?.total_received ?? 0,
    },
    ...items.map((item) => ({
      key: item.receipt_account,
      label: item.receipt_account,
      meta: `${item.payment_count} 笔`,
      total: item.total_received,
    })),
  ];
});
const receiptDatePresetOptions = computed(() => [
  { key: "LAST_7_DAYS" as const, label: "最近7天" },
  { key: "LAST_30_DAYS" as const, label: "最近30天" },
  { key: "THIS_MONTH" as const, label: "本月" },
  { key: "LAST_MONTH" as const, label: "上月" },
]);

const receiptFilterChips = computed(() =>
  [
    receiptAccount.value ? { key: "account" as const, label: `账户：${receiptAccount.value}` } : null,
    dateRange.value?.[0] && dateRange.value?.[1]
      ? {
          key: "date" as const,
          label: receiptDatePreset.value
            ? `时间：${receiptDatePresetLabel(receiptDatePreset.value)}`
            : `时间：${dateRange.value[0]} 至 ${dateRange.value[1]}`,
        }
      : null,
  ].filter(Boolean) as Array<{ key: "account" | "date"; label: string }>,
);
const activeFilterChips = computed(() => receiptFilterChips.value.map((item) => item.label));

function getMonthToken(offset = 0) {
  const current = new Date(`${todayInBrowserTimeZone()}T00:00:00`);
  current.setMonth(current.getMonth() + offset);
  const year = current.getFullYear();
  const month = String(current.getMonth() + 1).padStart(2, "0");
  return `${year}-${month}`;
}

function formatAmount(value: number): string {
  const amount = Number(value || 0);
  return amount.toLocaleString("zh-CN", {
    minimumFractionDigits: Number.isInteger(amount) ? 0 : 2,
    maximumFractionDigits: 2,
  });
}

function receiptDatePresetLabel(preset: ReceiptDatePreset) {
  return receiptDatePresetOptions.value.find((item) => item.key === preset)?.label || "时间范围";
}

function getReceiptPresetRange(preset: ReceiptDatePreset): [string, string] | null {
  if (preset === "LAST_7_DAYS") {
    const end = todayInBrowserTimeZone();
    const start = addDaysToDateString(end, -6);
    return start ? [start, end] : null;
  }
  if (preset === "LAST_30_DAYS") {
    const end = todayInBrowserTimeZone();
    const start = addDaysToDateString(end, -29);
    return start ? [start, end] : null;
  }
  if (preset === "THIS_MONTH") {
    return getMonthDateRange(getMonthToken());
  }
  return getMonthDateRange(getMonthToken(-1));
}

function syncReceiptDatePreset() {
  if (!dateRange.value?.[0] || !dateRange.value?.[1]) {
    receiptDatePreset.value = "";
    return;
  }
  const currentToken = `${dateRange.value[0]}|${dateRange.value[1]}`;
  const matched = receiptDatePresetOptions.value.find((item) => {
    const range = getReceiptPresetRange(item.key);
    return range ? `${range[0]}|${range[1]}` === currentToken : false;
  });
  receiptDatePreset.value = matched?.key || "";
}

function buildVoucherNo(row: { payment_id: number | null; billing_record_id: number | null }) {
  if (row.payment_id) return `收-${String(row.payment_id).padStart(4, "0")}`;
  if (row.billing_record_id) return `记-${String(row.billing_record_id).padStart(4, "0")}`;
  return "-";
}

function applyRouteQuery() {
  const queryAccount = typeof route.query.account === "string" ? route.query.account.trim() : "";
  const queryMonth = typeof route.query.month === "string" ? route.query.month.trim() : "";
  receiptAccount.value = queryAccount;
  dateRange.value = getMonthDateRange(queryMonth);
  syncReceiptDatePreset();
}

async function fetchReceiptLedger() {
  loading.value = true;
  try {
    const params: Record<string, string> = {};
    if (receiptAccount.value) params.receipt_account = receiptAccount.value;
    if (dateRange.value?.[0]) params.date_from = dateRange.value[0];
    if (dateRange.value?.[1]) params.date_to = dateRange.value[1];
    const resp = await apiClient.get<BillingReceiptAccountLedgerData>("/billing-records/receipt-account-ledger", {
      params,
    });
    data.value = resp.data;
  } catch (error: any) {
    data.value = null;
    ElMessage.error(error?.response?.data?.detail ?? "加载到账核对失败");
  } finally {
    loading.value = false;
    receiptHydrated.value = true;
  }
}

async function applyAccount(accountName: string) {
  receiptAccount.value = accountName;
  await fetchReceiptLedger();
}

async function resetFilters() {
  receiptAccount.value = "";
  dateRange.value = null;
  receiptDatePreset.value = "";
  await fetchReceiptLedger();
}

async function applyMobileFilters() {
  showMobileFilters.value = false;
  await fetchReceiptLedger();
}

function applyDatePreset(preset: ReceiptDatePreset) {
  receiptDatePreset.value = preset;
  dateRange.value = getReceiptPresetRange(preset);
}

async function removeReceiptFilterChip(key: "account" | "date") {
  if (key === "account") receiptAccount.value = "";
  if (key === "date") {
    dateRange.value = null;
    receiptDatePreset.value = "";
  }
  await fetchReceiptLedger();
}

onMounted(async () => {
  applyRouteQuery();
  await fetchReceiptLedger();
});

watch(
  () => route.fullPath,
  async () => {
    applyRouteQuery();
    await fetchReceiptLedger();
  },
);

watch(
  () => dateRange.value,
  () => {
    syncReceiptDatePreset();
  },
  { deep: true },
);
</script>

<template>
  <section v-if="isMobileWorkflow" class="mobile-page receipt-mobile-page">
    <section v-loading="loading && receiptHydrated" class="mobile-shell-panel">
      <template v-if="showReceiptInitialSkeleton">
        <div class="receipt-mobile-summary-head">
          <div class="receipt-mobile-skeleton-copy">
            <div class="mobile-skeleton-line is-lg"></div>
            <div class="mobile-skeleton-line is-md"></div>
          </div>
          <div class="mobile-skeleton-button"></div>
        </div>
        <div class="receipt-mobile-stat-grid">
          <article v-for="index in 3" :key="`receipt-stat-skeleton-${index}`" class="receipt-mobile-stat-card receipt-mobile-skeleton-stat">
            <div class="mobile-skeleton-line is-xs"></div>
            <div class="mobile-skeleton-line is-sm"></div>
          </article>
        </div>
        <div class="mobile-filter-presets receipt-mobile-presets receipt-mobile-skeleton-presets">
          <div v-for="index in 3" :key="`receipt-preset-skeleton-${index}`" class="mobile-filter-preset receipt-mobile-skeleton-preset">
            <div class="mobile-skeleton-line is-sm"></div>
            <div class="mobile-skeleton-line is-xs"></div>
          </div>
        </div>
      </template>
      <template v-else>
        <div class="receipt-mobile-summary-head">
          <div>
            <div class="receipt-mobile-summary-title">{{ selectedAccountLabel }}</div>
            <div class="receipt-mobile-summary-copy">{{ scopeLabel }}</div>
          </div>
          <el-button class="mobile-row-secondary-button" plain :icon="Filter" @click="showMobileFilters = true">
            筛选
          </el-button>
        </div>
        <div class="receipt-mobile-stat-grid">
          <article class="receipt-mobile-stat-card">
            <span>期初余额</span>
            <strong>{{ formatAmount(data?.opening_balance ?? 0) }}</strong>
          </article>
          <article class="receipt-mobile-stat-card">
            <span>借方合计</span>
            <strong>{{ formatAmount(data?.total_received ?? 0) }}</strong>
          </article>
          <article class="receipt-mobile-stat-card">
            <span>收款笔数</span>
            <strong>{{ data?.payment_count ?? 0 }}</strong>
          </article>
        </div>
        <div class="mobile-filter-presets receipt-mobile-presets">
          <button
            v-for="item in mobileAccountPresets"
            :key="`receipt-preset-${item.key || 'all'}`"
            type="button"
            class="mobile-filter-preset"
            :class="{ active: receiptAccount === item.key }"
            @click="applyAccount(item.key)"
          >
            <span>{{ item.label }}</span>
            <strong>{{ item.total }}</strong>
          </button>
        </div>
      </template>
      <div v-if="!showReceiptInitialSkeleton && activeFilterChips.length" class="mobile-chip-row receipt-mobile-chip-row">
        <button
          v-for="chip in receiptFilterChips"
          :key="chip.key"
          type="button"
          class="mobile-chip-button"
          @click="removeReceiptFilterChip(chip.key)"
        >
          <span>{{ chip.label }}</span>
          <span class="mobile-chip-close">移除</span>
        </button>
        <button type="button" class="receipt-clear-chip" @click="resetFilters">清空</button>
      </div>
    </section>

    <section class="mobile-shell-panel">
      <div class="receipt-mobile-list-head">
        <div>
          <div class="receipt-mobile-summary-title">到账流水</div>
          <div class="receipt-mobile-summary-copy">先看账户，再核对金额和凭证。</div>
        </div>
        <div v-if="showReceiptInitialSkeleton" class="mobile-skeleton-chip receipt-mobile-count-skeleton"></div>
        <el-tag v-else class="mobile-count-tag" size="small" effect="plain">{{ visibleEntries.length }} 条</el-tag>
      </div>

      <div v-loading="loading && receiptHydrated" class="receipt-mobile-list">
        <template v-if="showReceiptInitialSkeleton">
          <article
            v-for="index in 4"
            :key="`receipt-row-skeleton-${index}`"
            class="receipt-mobile-item receipt-mobile-skeleton-row"
          >
            <div class="receipt-mobile-top">
              <div class="receipt-mobile-skeleton-copy">
                <div class="mobile-skeleton-line is-lg"></div>
                <div class="mobile-skeleton-line is-xl"></div>
              </div>
              <div class="mobile-skeleton-line is-sm receipt-mobile-skeleton-amount"></div>
            </div>
            <div class="receipt-mobile-skeleton-meta">
              <div v-for="metaIndex in 4" :key="`receipt-meta-skeleton-${index}-${metaIndex}`" class="mobile-skeleton-line is-sm"></div>
            </div>
          </article>
        </template>
        <div v-else-if="!visibleEntries.length" class="mobile-empty-block">
          <div class="mobile-empty-kicker">到账流水</div>
          <div class="mobile-empty-title">当前筛选范围内没有到账流水</div>
          <div class="mobile-empty-copy">切换账户或时间预设，继续核对当前范围内的回款记录。</div>
        </div>
        <template v-else>
          <article
            v-for="row in visibleEntries"
            :key="`${row.occurred_at}-${row.customer_name}-${row.debit_amount}`"
            class="receipt-mobile-item"
          >
            <div class="receipt-mobile-top">
              <div>
                <div class="receipt-mobile-company">{{ row.customer_name }}</div>
                <div class="receipt-mobile-summary">{{ row.summary }}</div>
              </div>
              <div class="receipt-mobile-amount">{{ formatAmount(row.debit_amount - row.credit_amount) }}</div>
            </div>
            <div class="receipt-mobile-meta">
              <span>{{ row.occurred_at }}</span>
              <span>{{ buildVoucherNo(row) }}</span>
              <span>{{ row.receipt_account }}</span>
              <span>余额 {{ formatAmount(row.balance) }}</span>
              <span>{{ row.actor_username || "-" }}</span>
            </div>
          </article>
        </template>
      </div>
    </section>

    <MobileFilterSheet
      v-model="showMobileFilters"
      title="筛选到账流水"
      subtitle="先缩小账户和时间范围。"
      :summary-items="activeFilterChips"
      empty-summary="当前未设置筛选条件"
    >
      <el-form label-position="top" class="receipt-mobile-filter-form">
        <el-form-item label="入账账户">
          <el-select v-model="receiptAccount" clearable filterable placeholder="全部账户">
            <el-option
              v-for="item in accountOptions"
              :key="`receipt-mobile-${item.value}`"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="时间快捷预设">
          <div class="mobile-filter-presets receipt-mobile-date-presets">
            <button
              v-for="item in receiptDatePresetOptions"
              :key="item.key"
              type="button"
              class="mobile-filter-preset"
              :class="{ active: receiptDatePreset === item.key }"
              @click="applyDatePreset(item.key)"
            >
              <span>{{ item.label }}</span>
            </button>
          </div>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            format="YYYY-MM-DD"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            unlink-panels
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetFilters">重置</el-button>
        <el-button type="primary" @click="applyMobileFilters">应用筛选</el-button>
      </template>
    </MobileFilterSheet>
  </section>

  <div v-else class="receipt-page">
    <section class="receipt-header">
      <div>
        <div class="receipt-eyebrow">到账核对</div>
        <h1 class="receipt-title">按入账账户核对收款流水</h1>
        <p class="receipt-copy">{{ scopeLabel }}。左侧按账户切换，右侧核对收款明细。</p>
      </div>
      <div class="receipt-header-stats">
        <div class="receipt-stat-block">
          <span class="receipt-stat-label">期初借方</span>
          <strong class="receipt-stat-value">{{ formatAmount(data?.opening_debit ?? 0) }}</strong>
        </div>
        <div class="receipt-stat-block">
          <span class="receipt-stat-label">期初贷方</span>
          <strong class="receipt-stat-value">{{ formatAmount(data?.opening_credit ?? 0) }}</strong>
        </div>
        <div class="receipt-stat-block">
          <span class="receipt-stat-label">期初余额</span>
          <strong class="receipt-stat-value">{{ formatAmount(data?.opening_balance ?? 0) }}</strong>
        </div>
      </div>
    </section>

    <section class="receipt-toolbar">
      <el-form inline class="receipt-toolbar-form" @submit.prevent="fetchReceiptLedger">
        <el-form-item label="入账账户">
          <el-select v-model="receiptAccount" clearable filterable placeholder="全部账户">
            <el-option
              v-for="item in accountOptions"
              :key="`receipt-page-${item.value}`"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            format="YYYY-MM-DD"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            unlink-panels
          />
        </el-form-item>
        <el-form-item>
          <el-button size="small" type="primary" :loading="loading" @click="fetchReceiptLedger">查询</el-button>
          <el-button size="small" @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </section>

    <section class="receipt-workspace" :class="{ mobile: isMobile }">
      <aside class="receipt-sidebar">
        <div class="receipt-sidebar-head">
          <div class="receipt-sidebar-title">账户汇总</div>
          <div class="receipt-sidebar-copy">点账户名直接切换到账流水。</div>
        </div>

        <button class="receipt-account-item" :class="{ active: receiptAccount === '' }" @click="applyAccount('')">
          <div>
            <div class="receipt-account-title">全部账户</div>
            <div class="receipt-account-note">当前筛选范围内的全部到账</div>
          </div>
          <strong class="receipt-account-total">{{ formatAmount(data?.total_received ?? 0) }}</strong>
        </button>

        <button
          v-for="item in data?.account_summaries || []"
          :key="item.receipt_account"
          class="receipt-account-item"
          :class="{ active: receiptAccount === item.receipt_account }"
          @click="applyAccount(item.receipt_account)"
        >
          <div>
            <div class="receipt-account-title">{{ item.receipt_account }}</div>
            <div class="receipt-account-note">{{ item.payment_count }} 笔 · 最近 {{ item.last_received_at || '-' }}</div>
          </div>
          <strong class="receipt-account-total">{{ formatAmount(item.total_received) }}</strong>
        </button>
      </aside>

      <div class="receipt-main">
        <div class="receipt-main-head">
          <div>
            <div class="receipt-main-title">{{ selectedAccountLabel }}</div>
            <div class="receipt-main-copy">按银行日记账口径查看借方、贷方和运行余额。</div>
          </div>
          <el-tag size="small" type="success" effect="plain">{{ visibleEntries.length }} 条流水</el-tag>
        </div>

        <div v-if="isMobile" v-loading="loading" class="receipt-mobile-list">
          <article v-for="row in visibleEntries" :key="`${row.occurred_at}-${row.customer_name}-${row.debit_amount}`" class="receipt-mobile-item">
            <div class="receipt-mobile-top">
              <div>
                <div class="receipt-mobile-company">{{ row.customer_name }}</div>
                <div class="receipt-mobile-summary">{{ row.summary }}</div>
              </div>
              <div class="receipt-mobile-amount">{{ formatAmount(row.debit_amount - row.credit_amount) }}</div>
            </div>
            <div class="receipt-mobile-meta">
              <span>{{ row.occurred_at }}</span>
              <span>{{ buildVoucherNo(row) }}</span>
              <span>{{ row.receipt_account }}</span>
              <span>余额 {{ formatAmount(row.balance) }}</span>
              <span>{{ row.actor_username || '-' }}</span>
            </div>
          </article>
        </div>

        <el-table v-else v-loading="loading" :data="visibleEntries" stripe border size="small" class="receipt-table">
          <el-table-column prop="occurred_at" label="日期" width="108" />
          <el-table-column label="凭证号" width="100">
            <template #default="{ row }">
              {{ buildVoucherNo(row) }}
            </template>
          </el-table-column>
          <el-table-column prop="customer_name" label="公司名称" min-width="160" show-overflow-tooltip />
          <el-table-column prop="summary" label="摘要" min-width="240" show-overflow-tooltip />
          <el-table-column prop="debit_amount" label="借方" width="112" />
          <el-table-column prop="credit_amount" label="贷方" width="112" />
          <el-table-column prop="receipt_account" label="入账账户" width="180" show-overflow-tooltip />
          <el-table-column prop="balance" label="余额" width="118" />
          <el-table-column prop="actor_username" label="记录人" width="92" />
        </el-table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.receipt-mobile-page {
  gap: 12px;
}

.receipt-mobile-summary-head,
.receipt-mobile-list-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.receipt-mobile-summary-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.receipt-mobile-summary-copy {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--app-text-muted);
}

.receipt-mobile-skeleton-copy {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.receipt-mobile-stat-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 12px;
}

.receipt-mobile-skeleton-stat {
  justify-content: space-between;
}

.receipt-mobile-stat-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px;
  border: 1px solid var(--app-border-soft);
  background: var(--app-bg-soft);
}

.receipt-mobile-stat-card span {
  font-size: 11px;
  color: var(--app-text-muted);
}

.receipt-mobile-stat-card strong {
  font-size: 16px;
  color: var(--app-text-primary);
}

.receipt-mobile-presets {
  margin-top: 12px;
}

.receipt-mobile-skeleton-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.receipt-mobile-skeleton-preset {
  pointer-events: none;
}

.receipt-mobile-chip-row {
  margin-top: 10px;
}

.receipt-mobile-count-skeleton {
  flex-shrink: 0;
}

.receipt-clear-chip {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid var(--app-border-soft);
  background: transparent;
  font-size: 12px;
  color: var(--app-text-muted);
}

.receipt-mobile-date-presets {
  margin-top: 0;
}

.receipt-mobile-filter-form :deep(.el-form-item) {
  margin-bottom: 16px;
}

.receipt-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.receipt-header,
.receipt-toolbar,
.receipt-sidebar,
.receipt-main {
  background: #ffffff;
  border: 1px solid #dde5e7;
}

.receipt-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16px;
  padding: 18px 20px;
  border-top: 2px solid #4d8096;
}

.receipt-eyebrow {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: #5a7d72;
}

.receipt-title {
  margin: 4px 0 6px;
  font-size: 24px;
  line-height: 1.08;
  color: #172330;
}

.receipt-copy {
  margin: 0;
  max-width: 680px;
  font-size: 13px;
  line-height: 1.55;
  color: #61727e;
}

.receipt-header-stats {
  display: flex;
  align-items: stretch;
  gap: 8px;
}

.receipt-stat-block {
  min-width: 112px;
  padding: 10px 12px;
  background: #f5f8f8;
  border: 1px solid #dde5e7;
}

.receipt-stat-label {
  display: block;
  font-size: 11px;
  color: #6c7b87;
}

.receipt-stat-value {
  display: block;
  margin-top: 8px;
  font-size: 20px;
  line-height: 1;
  color: #132231;
}

.receipt-toolbar {
  padding: 12px 14px 2px;
}

.receipt-toolbar-form {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}

.receipt-toolbar-form :deep(.el-form-item) {
  margin-right: 10px;
  margin-bottom: 10px;
}

.receipt-toolbar-form :deep(.el-form-item__label) {
  font-size: 12px;
  color: #5f6f7a;
}

.receipt-toolbar-form :deep(.el-input__wrapper),
.receipt-toolbar-form :deep(.el-select__wrapper),
.receipt-toolbar-form :deep(.el-date-editor.el-input__wrapper) {
  min-height: 34px;
  min-width: 280px;
}

.receipt-workspace {
  display: grid;
  grid-template-columns: 248px minmax(0, 1fr);
  gap: 12px;
}

.receipt-workspace.mobile {
  grid-template-columns: 1fr;
}

.receipt-sidebar {
  padding: 12px 14px;
}

.receipt-sidebar-head {
  margin-bottom: 8px;
}

.receipt-sidebar-title,
.receipt-main-title {
  font-size: 15px;
  font-weight: 700;
  color: #182635;
}

.receipt-sidebar-copy,
.receipt-main-copy {
  margin-top: 3px;
  font-size: 12px;
  line-height: 1.5;
  color: #6c7b87;
}

.receipt-account-item {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 0;
  text-align: left;
  border: none;
  border-top: 1px solid #edf1f2;
  background: transparent;
  cursor: pointer;
}

.receipt-account-item.active {
  color: #265f77;
}

.receipt-account-title {
  font-size: 13px;
  font-weight: 600;
}

.receipt-account-note {
  margin-top: 3px;
  font-size: 11px;
  color: #71808b;
}

.receipt-account-total {
  font-size: 15px;
  font-weight: 700;
  color: #1e4e64;
}

.receipt-main {
  padding: 12px 14px;
}

.receipt-main-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.receipt-table :deep(.el-table__cell) {
  padding: 8px 0;
}

.receipt-mobile-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.receipt-mobile-skeleton-row {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.receipt-mobile-skeleton-amount {
  flex-shrink: 0;
  width: 72px;
}

.receipt-mobile-skeleton-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.receipt-mobile-item {
  padding: 10px 12px;
  background: #f7f9f9;
  border: 1px solid #e4eaec;
}

.receipt-mobile-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.receipt-mobile-company {
  font-weight: 700;
  color: #172330;
}

.receipt-mobile-summary {
  margin-top: 4px;
  color: #647783;
  line-height: 1.5;
}

.receipt-mobile-amount {
  white-space: nowrap;
  font-weight: 700;
  color: #1e4e64;
}

.receipt-mobile-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  margin-top: 8px;
  font-size: 12px;
  color: #72818d;
}

@media (max-width: 960px) {
  .receipt-header {
    grid-template-columns: 1fr;
  }

  .receipt-header-stats {
    flex-wrap: wrap;
  }
}

@media (max-width: 640px) {
  .receipt-title {
    font-size: 20px;
  }

  .receipt-header,
  .receipt-sidebar,
  .receipt-main {
    padding: 14px;
  }

  .receipt-toolbar {
    padding: 10px 12px 0;
  }

  .receipt-stat-block {
    flex: 1 1 calc(50% - 4px);
    min-width: 0;
  }

  .receipt-mobile-skeleton-meta {
    grid-template-columns: 1fr;
  }
}
</style>
