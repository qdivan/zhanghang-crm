<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { apiClient } from "../api/client";
import type { BillingCustomerSummaryItem, BillingSummaryData } from "../types";
import { todayInBrowserTimeZone } from "../utils/time";

type CostInsightKey = "RECEIVABLE" | "RECEIVED" | "GAP" | "OVERDUE";

const router = useRouter();
const loading = ref(false);
const dateRange = ref<[string, string]>(getDefaultRange());
const activeInsight = ref<CostInsightKey>("OVERDUE");
const summary = ref<BillingSummaryData>({
  total_records: 0,
  total_fee: 0,
  total_monthly_fee: 0,
  payment_method_distribution: [],
  status_distribution: [],
  receipt_account_distribution: [],
  summary_date_from: null,
  summary_date_to: null,
  customer_summaries: [],
});

function getDefaultRange(): [string, string] {
  const today = todayInBrowserTimeZone();
  const [yearText] = today.split("-");
  return [`${String(Number(yearText) - 1)}-01-01`, today];
}

function formatAmount(value: number): string {
  const amount = Number(value || 0);
  return amount.toLocaleString("zh-CN", {
    minimumFractionDigits: Number.isInteger(amount) ? 0 : 2,
    maximumFractionDigits: 2,
  });
}

const receivableTotal = computed(() =>
  summary.value.customer_summaries.reduce((sum, item) => sum + Number(item.period_receivable || 0), 0),
);

const receivedTotal = computed(() =>
  summary.value.customer_summaries.reduce((sum, item) => sum + Number(item.period_received || 0), 0),
);

const outstandingGap = computed(() =>
  summary.value.customer_summaries.reduce((sum, item) => sum + Number(item.ending_outstanding || 0), 0),
);

const overdueCustomerCount = computed(() =>
  summary.value.customer_summaries.filter((item) => item.overdue_count > 0).length,
);

const insightCards = computed(() => [
  {
    key: "RECEIVABLE" as const,
    label: "本期应收",
    value: formatAmount(receivableTotal.value),
    note: "点击后看当前范围内有应收的客户总况",
    tone: "primary",
  },
  {
    key: "RECEIVED" as const,
    label: "本期实收",
    value: formatAmount(receivedTotal.value),
    note: "点击后看本期已经收到款的客户",
    tone: "success",
  },
  {
    key: "GAP" as const,
    label: "应收回款差额",
    value: formatAmount(outstandingGap.value),
    note: "点击后看仍存在未收差额的客户",
    tone: "danger",
  },
  {
    key: "OVERDUE" as const,
    label: "逾期客户数",
    value: String(overdueCustomerCount.value),
    note: "点击后看逾期客户收费总况",
    tone: "warning",
  },
]);

const insightRows = computed<BillingCustomerSummaryItem[]>(() => {
  if (activeInsight.value === "RECEIVABLE") {
    return summary.value.customer_summaries.filter((item) => Number(item.period_receivable || 0) > 0);
  }
  if (activeInsight.value === "RECEIVED") {
    return summary.value.customer_summaries.filter((item) => Number(item.period_received || 0) > 0);
  }
  if (activeInsight.value === "GAP") {
    return summary.value.customer_summaries.filter((item) => Number(item.ending_outstanding || 0) > 0);
  }
  return summary.value.customer_summaries.filter((item) => item.overdue_count > 0);
});

const insightTitle = computed(() => {
  if (activeInsight.value === "RECEIVABLE") return "本期应收客户总况";
  if (activeInsight.value === "RECEIVED") return "本期实收客户总况";
  if (activeInsight.value === "GAP") return "应收与回款存在差额的客户";
  return "逾期客户收费总况";
});

async function fetchData() {
  loading.value = true;
  try {
    const summaryResp = await apiClient.get<BillingSummaryData>("/billing-records/summary", {
      params: {
        date_from: dateRange.value[0],
        date_to: dateRange.value[1],
      },
    });
    summary.value = summaryResp.data;
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "加载老板视图失败");
  } finally {
    loading.value = false;
  }
}

function openBillingInsight() {
  const query: Record<string, string> = {
    view: activeInsight.value === "RECEIVED" ? "payments" : "summary",
  };
  if (activeInsight.value === "OVERDUE") {
    query.status = "FULL_ARREARS";
  }
  router.push({ path: "/billing", query });
}

onMounted(async () => {
  await fetchData();
});
</script>

<template>
  <section class="cost-view-page">
    <el-card shadow="never" class="cost-head-card">
      <div class="cost-head">
        <div>
          <div class="cost-title">成本与老板视图</div>
          <div class="cost-copy">默认看上年 1 月 1 日至今的经营情况。点卡片就会切到对应客户明细，不再只是说明文字。</div>
        </div>
        <el-form inline class="cost-filter-form" @submit.prevent="fetchData">
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
            <el-button type="primary" :loading="loading" @click="fetchData">刷新</el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-card>

    <section class="cost-card-grid">
      <article
        v-for="item in insightCards"
        :key="item.key"
        class="cost-card"
        :class="[item.tone, { active: activeInsight === item.key }]"
        @click="activeInsight = item.key"
      >
        <div class="cost-card-label">{{ item.label }}</div>
        <div class="cost-card-value">{{ item.value }}</div>
        <div class="cost-card-note">{{ item.note }}</div>
      </article>
    </section>

    <el-card shadow="never" class="cost-detail-card">
      <template #header>
        <div class="cost-section-head">
          <div>
            <div class="cost-section-title">{{ insightTitle }}</div>
            <div class="cost-section-copy">这里只显示当前指标对应的客户收费总况。需要继续操作时可以跳到收费明细工作台。</div>
          </div>
          <el-button plain @click="openBillingInsight">打开收费明细</el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="insightRows" stripe border size="small" class="cost-detail-table">
        <el-table-column prop="customer_name" label="客户名称" min-width="180" fixed="left" />
        <el-table-column prop="customer_contact_name" label="联系人" width="120" />
        <el-table-column prop="opening_arrears" label="期初欠款" width="118" />
        <el-table-column prop="period_receivable" label="本期应收" width="118" />
        <el-table-column prop="period_received" label="本期实收" width="118" />
        <el-table-column prop="ending_outstanding" label="应收回款差额" width="128" />
        <el-table-column prop="overdue_count" label="逾期条数" width="96" />
        <el-table-column prop="latest_activity_content" label="最近跟进" min-width="220" show-overflow-tooltip />
      </el-table>
    </el-card>
  </section>
</template>

<style scoped>
.cost-view-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.cost-head-card,
.cost-detail-card {
  border-color: #dfe6e8;
}

.cost-head,
.cost-section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.cost-title,
.cost-section-title {
  font-size: 18px;
  font-weight: 700;
  color: #172330;
}

.cost-copy,
.cost-section-copy,
.cost-card-note {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: #667085;
}

.cost-card-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.cost-card {
  padding: 14px 16px;
  border: 1px solid #dde5e7;
  background: #ffffff;
  cursor: pointer;
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}

.cost-card:hover,
.cost-card.active {
  transform: translateY(-1px);
  border-color: #8fb2be;
  box-shadow: 0 10px 24px rgba(15, 35, 55, 0.08);
}

.cost-card.primary {
  background: linear-gradient(135deg, rgba(77, 128, 150, 0.12), rgba(255, 255, 255, 0.98));
}

.cost-card.success {
  background: linear-gradient(135deg, rgba(49, 126, 74, 0.12), rgba(255, 255, 255, 0.98));
}

.cost-card.warning {
  background: linear-gradient(135deg, rgba(208, 151, 48, 0.12), rgba(255, 255, 255, 0.98));
}

.cost-card.danger {
  background: linear-gradient(135deg, rgba(187, 77, 77, 0.12), rgba(255, 255, 255, 0.98));
}

.cost-card-label {
  font-size: 12px;
  color: #5f6f7a;
}

.cost-card-value {
  margin-top: 10px;
  font-size: 24px;
  font-weight: 700;
  color: #172330;
}

.cost-filter-form :deep(.el-date-editor.el-input__wrapper) {
  min-width: 280px;
}

@media (max-width: 960px) {
  .cost-card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .cost-head,
  .cost-section-head {
    flex-direction: column;
  }
}

@media (max-width: 640px) {
  .cost-card-grid {
    grid-template-columns: 1fr;
  }
}
</style>
