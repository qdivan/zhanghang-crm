<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

import { apiClient } from "../api/client";
import { useResponsive } from "../composables/useResponsive";
import { useAuthStore } from "../stores/auth";
import type { BillingReceiptAccountLedgerData } from "../types";
import { getMonthDateRange, receiptAccountOptions } from "./billing/viewMeta";

const route = useRoute();
const auth = useAuthStore();
const { isMobile } = useResponsive();

const loading = ref(false);
const receiptAccount = ref("");
const dateRange = ref<[string, string] | null>(null);
const data = ref<BillingReceiptAccountLedgerData | null>(null);

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
  if (auth.user?.role === "MANAGER") return "当前按直属下属范围核对到账流水";
  if (auth.user?.role === "ADMIN") return "当前按管理员可见范围核对到账流水";
  if (auth.user?.role === "ACCOUNTANT") return "当前按收费只读授权范围核对到账流水";
  return "当前按全公司范围核对到账流水";
});

const selectedAccountLabel = computed(() => receiptAccount.value || "全部账户");
const accountCount = computed(() => data.value?.account_summaries.length ?? 0);
const visibleEntries = computed(() => data.value?.entries || []);

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
  }
}

async function applyAccount(accountName: string) {
  receiptAccount.value = accountName;
  await fetchReceiptLedger();
}

async function resetFilters() {
  receiptAccount.value = "";
  dateRange.value = null;
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
</script>

<template>
  <div class="receipt-page">
    <section class="receipt-header">
      <div>
        <div class="receipt-eyebrow">到账核对</div>
        <h1 class="receipt-title">按入账账户核对收款流水</h1>
        <p class="receipt-copy">
          {{ scopeLabel }}。这里专门看各账户收了几笔、合计多少、分别收了哪些公司的款。
        </p>
      </div>
      <div class="receipt-header-stats">
        <div class="receipt-stat-block">
          <span class="receipt-stat-label">收款笔数</span>
          <strong class="receipt-stat-value">{{ data?.payment_count ?? 0 }}</strong>
        </div>
        <div class="receipt-stat-block">
          <span class="receipt-stat-label">入账合计</span>
          <strong class="receipt-stat-value">{{ data?.total_received ?? 0 }}</strong>
        </div>
        <div class="receipt-stat-block">
          <span class="receipt-stat-label">账户数</span>
          <strong class="receipt-stat-value">{{ accountCount }}</strong>
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
          <el-button type="primary" :loading="loading" @click="fetchReceiptLedger">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </section>

    <section class="receipt-workspace" :class="{ mobile: isMobile }">
      <aside class="receipt-sidebar">
        <div class="receipt-sidebar-head">
          <div class="receipt-sidebar-title">账户汇总</div>
          <div class="receipt-sidebar-copy">点账户名可直接切换到该账户的到账流水。</div>
        </div>

        <button
          class="receipt-account-item"
          :class="{ active: receiptAccount === '' }"
          @click="applyAccount('')"
        >
          <div>
            <div class="receipt-account-title">全部账户</div>
            <div class="receipt-account-note">查看当前筛选范围内的全部到账</div>
          </div>
          <strong class="receipt-account-total">{{ data?.total_received ?? 0 }}</strong>
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
            <div class="receipt-account-note">
              {{ item.payment_count }} 笔 · 最近 {{ item.last_received_at || '-' }}
            </div>
          </div>
          <strong class="receipt-account-total">{{ item.total_received }}</strong>
        </button>
      </aside>

      <div class="receipt-main">
        <div class="receipt-main-head">
          <div>
            <div class="receipt-main-title">{{ selectedAccountLabel }}</div>
            <div class="receipt-main-copy">贷方表示实收金额；累计入账用于核对该筛选范围下的到账累积。</div>
          </div>
          <el-tag type="success" effect="plain">{{ visibleEntries.length }} 条流水</el-tag>
        </div>

        <div v-if="isMobile" v-loading="loading" class="receipt-mobile-list">
          <article v-for="row in visibleEntries" :key="`${row.occurred_at}-${row.customer_name}-${row.received_amount}`" class="receipt-mobile-item">
            <div class="receipt-mobile-top">
              <div>
                <div class="receipt-mobile-company">{{ row.customer_name }}</div>
                <div class="receipt-mobile-summary">{{ row.summary }}</div>
              </div>
              <div class="receipt-mobile-amount">{{ row.received_amount }}</div>
            </div>
            <div class="receipt-mobile-meta">
              <span>{{ row.occurred_at }}</span>
              <span>{{ buildVoucherNo(row) }}</span>
              <span>{{ row.receipt_account }}</span>
              <span>累计 {{ row.cumulative_received }}</span>
              <span>{{ row.actor_username || '-' }}</span>
            </div>
          </article>
        </div>

        <el-table v-else v-loading="loading" :data="visibleEntries" stripe border class="receipt-table">
          <el-table-column prop="occurred_at" label="日期" width="120" />
          <el-table-column label="凭证号" width="120">
            <template #default="{ row }">
              {{ buildVoucherNo(row) }}
            </template>
          </el-table-column>
          <el-table-column prop="customer_name" label="公司名称" min-width="180" show-overflow-tooltip />
          <el-table-column prop="summary" label="摘要" min-width="280" show-overflow-tooltip />
          <el-table-column prop="received_amount" label="贷方(收款)" width="120" />
          <el-table-column prop="receipt_account" label="入账账户" width="120" />
          <el-table-column prop="cumulative_received" label="累计入账" width="130" />
          <el-table-column prop="actor_username" label="记录人" width="100" />
        </el-table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.receipt-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
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
  gap: 20px;
  padding: 22px 24px;
  border-top: 3px solid #4d8096;
}

.receipt-eyebrow {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: #5a7d72;
}

.receipt-title {
  margin: 6px 0 8px;
  font-size: 30px;
  line-height: 1.1;
  color: #172330;
}

.receipt-copy {
  margin: 0;
  max-width: 760px;
  color: #61727e;
  line-height: 1.7;
}

.receipt-header-stats {
  display: flex;
  align-items: stretch;
  gap: 12px;
}

.receipt-stat-block {
  min-width: 126px;
  padding: 12px 14px;
  background: #f5f8f8;
  border: 1px solid #dde5e7;
}

.receipt-stat-label {
  display: block;
  font-size: 12px;
  color: #6c7b87;
}

.receipt-stat-value {
  display: block;
  margin-top: 10px;
  font-size: 24px;
  line-height: 1;
  color: #132231;
}

.receipt-toolbar {
  padding: 14px 16px 0;
}

.receipt-toolbar-form {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}

.receipt-workspace {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 16px;
}

.receipt-workspace.mobile {
  grid-template-columns: 1fr;
}

.receipt-sidebar {
  padding: 16px;
}

.receipt-sidebar-head {
  margin-bottom: 12px;
}

.receipt-sidebar-title,
.receipt-main-title {
  font-size: 16px;
  font-weight: 700;
  color: #182635;
}

.receipt-sidebar-copy,
.receipt-main-copy {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.6;
  color: #6c7b87;
}

.receipt-account-item {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 0;
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
  font-size: 14px;
  font-weight: 600;
}

.receipt-account-note {
  margin-top: 4px;
  font-size: 12px;
  color: #71808b;
}

.receipt-account-total {
  font-size: 16px;
  font-weight: 700;
  color: #1e4e64;
}

.receipt-main {
  padding: 16px;
}

.receipt-main-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.receipt-mobile-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.receipt-mobile-item {
  padding: 12px;
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
  line-height: 1.6;
}

.receipt-mobile-amount {
  white-space: nowrap;
  font-weight: 700;
  color: #1e4e64;
}

.receipt-mobile-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 12px;
  margin-top: 10px;
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
    font-size: 22px;
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
    flex: 1 1 calc(50% - 6px);
    min-width: 0;
  }
}
</style>
