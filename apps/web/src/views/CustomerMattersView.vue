<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, nextTick, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { apiClient } from "../api/client";
import FlexibleDateInput from "../components/shared/FlexibleDateInput.vue";
import { isMobileAppPath } from "../mobile/config";
import { useAuthStore } from "../stores/auth";
import type { CustomerDetail, CustomerMatterSummaryItem, CustomerTimelineEntry, CustomerTimelineEventCreatePayload } from "../types";
import { todayInBrowserTimeZone } from "../utils/time";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const loading = ref(false);
const detailLoading = ref(false);
const submitting = ref(false);
const rows = ref<CustomerMatterSummaryItem[]>([]);
const detail = ref<CustomerDetail | null>(null);
const keyword = ref("");
const selectedCustomerId = ref<number | null>(null);
const matterFormAnchor = ref<HTMLElement | null>(null);
const matterContentInput = ref<{ focus?: () => void } | null>(null);
const isMobileWorkflow = computed(() => isMobileAppPath(route.path));

const form = reactive<CustomerTimelineEventCreatePayload>({
  occurred_at: todayInBrowserTimeZone(),
  event_type: "DELIVERY",
  status: "OPEN",
  reminder_at: todayInBrowserTimeZone(),
  completed_at: null,
  content: "",
  note: "",
  result: "",
  amount: null,
});

const eventTypeOptions = [
  { label: "客户需补资料", value: "DOCUMENT" },
  { label: "客户需去办理", value: "DELIVERY" },
  { label: "内部提醒", value: "MEETING" },
  { label: "证照/发票/社保", value: "OTHER" },
];

const statusOptions = [
  { label: "待跟进", value: "OPEN" },
  { label: "仅记录", value: "NOTE" },
  { label: "已办结", value: "DONE" },
];

const selectedSummaryRow = computed(
  () => rows.value.find((item) => item.customer_id === selectedCustomerId.value) || null,
);

const matterRows = computed(() =>
  (detail.value?.timeline || []).filter((item) => item.source_type === "CUSTOMER_EVENT"),
);

const canWriteCustomer = computed(() => {
  if (!detail.value) return false;
  if (auth.user?.role !== "ACCOUNTANT") return true;
  return (
    detail.value.accountant_username === auth.user.username
    || detail.value.responsible_username === auth.user.username
  );
});

const canDeleteMatter = computed(() => auth.user?.role === "OWNER" || auth.user?.role === "ADMIN");

function matterStatusLabel(statusValue: string) {
  if (statusValue === "DONE") return "已办结";
  if (statusValue === "OPEN") return "待跟进";
  return "仅记录";
}

function matterStatusTag(statusValue: string): "success" | "warning" | "info" {
  if (statusValue === "DONE") return "success";
  if (statusValue === "OPEN") return "warning";
  return "info";
}

function matterTypeLabel(item: CustomerTimelineEntry) {
  return item.title || "重要事项";
}

function resetForm() {
  form.occurred_at = todayInBrowserTimeZone();
  form.event_type = "DELIVERY";
  form.status = "OPEN";
  form.reminder_at = todayInBrowserTimeZone();
  form.completed_at = null;
  form.content = "";
  form.note = "";
  form.result = "";
  form.amount = null;
}

async function fetchSummary() {
  loading.value = true;
  try {
    const resp = await apiClient.get<CustomerMatterSummaryItem[]>("/customers/matters/summary", {
      params: { keyword: keyword.value || undefined },
    });
    rows.value = resp.data;
    if (!rows.value.length) {
      selectedCustomerId.value = null;
      detail.value = null;
      return;
    }
    const routeCustomerId = Number(route.query.customerId || route.query.customer_id || 0) || null;
    const preferredId =
      routeCustomerId && rows.value.some((item) => item.customer_id === routeCustomerId)
        ? routeCustomerId
        : selectedCustomerId.value && rows.value.some((item) => item.customer_id === selectedCustomerId.value)
          ? selectedCustomerId.value
          : rows.value[0].customer_id;
    await selectCustomer(preferredId);
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "获取重要事项失败");
  } finally {
    loading.value = false;
  }
}

async function fetchDetail(customerId: number) {
  detailLoading.value = true;
  try {
    const resp = await apiClient.get<CustomerDetail>(`/customers/${customerId}`);
    detail.value = resp.data;
  } catch (error: any) {
    detail.value = null;
    ElMessage.error(error?.response?.data?.detail ?? "获取客户事项失败");
  } finally {
    detailLoading.value = false;
  }
}

async function selectCustomer(customerId: number | null) {
  if (!customerId) return;
  selectedCustomerId.value = customerId;
  await fetchDetail(customerId);
  await router.replace({
    path: route.path,
    query: { ...route.query, customerId: String(customerId) },
  });
}

async function submitMatter() {
  if (!detail.value) {
    ElMessage.warning("请先选择客户");
    return;
  }
  if (!canWriteCustomer.value) {
    ElMessage.warning("当前账号没有这位客户的重要事项写权限");
    return;
  }
  if (!form.content.trim()) {
    ElMessage.warning("请先填写事项内容");
    return;
  }
  if (form.status === "OPEN" && !form.reminder_at) {
    ElMessage.warning("待跟进事项需要设置提醒日期");
    return;
  }
  submitting.value = true;
  try {
    await apiClient.post(`/customers/${detail.value.id}/timeline-events`, form);
    ElMessage.success("重要事项已保存");
    resetForm();
    await fetchDetail(detail.value.id);
    await fetchSummary();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "保存重要事项失败");
  } finally {
    submitting.value = false;
  }
}

async function markDone(item: CustomerTimelineEntry) {
  if (!detail.value) return;
  if (!canWriteCustomer.value) {
    ElMessage.warning("当前账号没有这位客户的重要事项写权限");
    return;
  }
  try {
    await apiClient.patch(`/customers/${detail.value.id}/timeline-events/${item.source_id}`, {
      status: "DONE",
      completed_at: todayInBrowserTimeZone(),
      result: item.result || "已完成",
    });
    ElMessage.success("事项已办结");
    await fetchDetail(detail.value.id);
    await fetchSummary();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "办结失败");
  }
}

async function removeMatter(item: CustomerTimelineEntry) {
  if (!detail.value || !canDeleteMatter.value) return;
  try {
    await apiClient.delete(`/customers/${detail.value.id}/timeline-events/${item.source_id}`);
    ElMessage.success("重要事项已删除");
    await fetchDetail(detail.value.id);
    await fetchSummary();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "删除失败");
  }
}

async function focusMatterForm() {
  if (!detail.value) {
    ElMessage.warning("请先从左侧选择客户");
    return;
  }
  await nextTick();
  matterFormAnchor.value?.scrollIntoView({ behavior: "smooth", block: "start" });
  window.setTimeout(() => matterContentInput.value?.focus?.(), 120);
}

function openCustomerDetail() {
  if (!detail.value) return;
  router.push(`${isMobileWorkflow.value ? "/m/customers" : "/customers"}/${detail.value.id}`);
}

onMounted(async () => {
  await fetchSummary();
});

watch(
  () => route.fullPath,
  async () => {
    const queryCustomerId = Number(route.query.customerId || route.query.customer_id || 0) || null;
    if (queryCustomerId && queryCustomerId !== selectedCustomerId.value) {
      await selectCustomer(queryCustomerId);
    }
  },
);
</script>

<template>
  <section class="customer-matters-page">
    <el-card shadow="never" class="matter-head-card">
      <div class="matter-head">
        <div>
          <div class="matter-title">重要事项</div>
          <div class="matter-copy">这里专门记录收费以外的重要提醒、客户需补资料和办理进度，作为会计维护客户的工作记事本。</div>
        </div>
      </div>
    </el-card>

    <section class="matter-workspace">
      <el-card shadow="never" class="matter-summary-card">
        <template #header>
          <div class="matter-section-head matter-summary-head">
            <div class="matter-section-copy-block">
              <div class="matter-section-title">客户列表 - 重要事项</div>
              <div class="matter-section-copy">先选客户，再在右侧集中处理这一户的事项。</div>
            </div>
            <div class="matter-summary-actions">
              <el-input
                v-model="keyword"
                placeholder="客户 / 联系人 / 电话 / 编号 / 服务项目"
                clearable
                @keyup.enter="fetchSummary"
              />
              <el-button type="primary" @click="fetchSummary">查询</el-button>
              <el-tag type="info" effect="plain">{{ rows.length }} 户</el-tag>
            </div>
          </div>
        </template>
        <el-table
          v-loading="loading"
          :data="rows"
          stripe
          border
          size="small"
          highlight-current-row
          :current-row-key="selectedCustomerId ?? undefined"
          row-key="customer_id"
          class="matter-summary-table"
          @row-click="selectCustomer($event.customer_id)"
        >
          <el-table-column label="客户" min-width="180" fixed="left">
            <template #default="{ row }">
              <div class="matter-customer-cell">
                <strong>{{ row.customer_name }}</strong>
                <span>{{ row.customer_code || "未编号" }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="service_start_display" label="服务开始" width="110" />
          <el-table-column prop="current_service_summary" label="当前服务项目" min-width="180" show-overflow-tooltip />
          <el-table-column prop="latest_reminder_at" label="最近提醒" width="110" />
          <el-table-column prop="open_item_count" label="待跟进" width="84" />
          <el-table-column prop="latest_progress" label="最近办理进度" min-width="220" show-overflow-tooltip />
        </el-table>
      </el-card>

      <el-card shadow="never" class="matter-detail-card">
        <template #header>
          <div class="matter-section-head matter-detail-head">
            <div class="matter-section-copy-block">
              <div class="matter-section-title">
                {{ selectedSummaryRow ? `${selectedSummaryRow.customer_name} 的重要事项` : "请选择客户" }}
              </div>
              <div class="matter-section-copy">
                {{ selectedSummaryRow ? `${selectedSummaryRow.current_service_summary} · 服务开始 ${selectedSummaryRow.service_start_display}` : "左侧选中一位客户后，这里会只显示该客户的重要事项。" }}
              </div>
            </div>
            <div class="matter-detail-header-actions">
              <el-button v-if="detail" type="primary" plain @click="focusMatterForm">新增重要事项</el-button>
              <el-button v-if="detail" plain @click="openCustomerDetail">打开客户档案</el-button>
            </div>
          </div>
        </template>

        <div v-if="!detail" class="matter-empty">
          <div class="matter-empty-title">还没有选中客户</div>
          <div class="matter-empty-copy">先从左侧客户列表里选一户，这里就会切到这家客户的事项专注视图。</div>
        </div>

        <template v-else>
          <div v-loading="detailLoading" class="matter-detail-body">
            <div class="matter-detail-topline">
              <el-tag type="warning" effect="plain">待跟进 {{ selectedSummaryRow?.open_item_count ?? 0 }}</el-tag>
              <el-tag type="info" effect="plain">联系人 {{ selectedSummaryRow?.customer_contact_name || detail.contact_name || "-" }}</el-tag>
            </div>

            <div v-if="!matterRows.length" class="matter-empty">
              <div class="matter-empty-title">这位客户还没有重要事项</div>
              <div class="matter-empty-copy">可以直接在下面新增提醒，例如补资料、办发票、去人社局或审批局等事项。</div>
            </div>

            <div v-else class="matter-list">
              <article v-for="item in matterRows" :key="`${item.source_id}-${item.occurred_at}`" class="matter-item">
                <div class="matter-item-head">
                  <div>
                    <div class="matter-item-title">{{ matterTypeLabel(item) }}</div>
                    <div class="matter-item-subtitle">{{ item.occurred_at }} · {{ item.actor_username || "系统" }}</div>
                  </div>
                  <el-tag size="small" :type="matterStatusTag(item.status)" effect="plain">
                    {{ matterStatusLabel(item.status) }}
                  </el-tag>
                </div>
                <div class="matter-item-content">{{ item.content }}</div>
                <div class="matter-item-meta">
                  <span v-if="item.reminder_at">提醒 {{ item.reminder_at }}</span>
                  <span v-if="item.completed_at">办结 {{ item.completed_at }}</span>
                  <span v-if="item.result">结果 {{ item.result }}</span>
                  <span v-if="item.note">备注 {{ item.note }}</span>
                </div>
                <div class="matter-item-actions">
                  <el-button
                    v-if="item.status !== 'DONE' && canWriteCustomer"
                    size="small"
                    type="primary"
                    plain
                    @click="markDone(item)"
                  >
                    办结
                  </el-button>
                  <el-popconfirm
                    v-if="canDeleteMatter"
                    title="确认删除这条重要事项吗？"
                    confirm-button-text="删除"
                    cancel-button-text="取消"
                    @confirm="removeMatter(item)"
                  >
                    <template #reference>
                      <el-button size="small" type="danger" plain>删除</el-button>
                    </template>
                  </el-popconfirm>
                </div>
              </article>
            </div>

            <el-divider />

            <div ref="matterFormAnchor">
            <el-form label-position="top" class="matter-form">
              <el-row :gutter="12">
                <el-col :xs="24" :sm="8">
                  <el-form-item label="记录日期">
                    <FlexibleDateInput v-model="form.occurred_at" :empty-value="''" />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :sm="8">
                  <el-form-item label="事项类型">
                    <el-select v-model="form.event_type" class="wide-field">
                      <el-option v-for="item in eventTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :sm="8">
                  <el-form-item label="状态">
                    <el-select v-model="form.status" class="wide-field">
                      <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="12">
                <el-col :xs="24" :sm="12">
                  <el-form-item v-if="form.status === 'OPEN'" label="提醒日期">
                    <FlexibleDateInput v-model="form.reminder_at" :empty-value="null" clearable />
                  </el-form-item>
                  <el-form-item v-else-if="form.status === 'DONE'" label="办结日期">
                    <FlexibleDateInput v-model="form.completed_at" :empty-value="null" clearable />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-form-item label="事项内容">
                <el-input
                  ref="matterContentInput"
                  v-model="form.content"
                  type="textarea"
                  :rows="3"
                  placeholder="例如：客户需发身份证、客户需去开房租发票、等审批局回执等"
                />
              </el-form-item>
              <el-form-item label="进度备注">
                <el-input v-model="form.note" type="textarea" :rows="2" placeholder="补充过程中的难点、阻塞点或下一步动作" />
              </el-form-item>
              <el-form-item v-if="form.status === 'DONE'" label="办理结果">
                <el-input v-model="form.result" type="textarea" :rows="2" placeholder="填写办结结果" />
              </el-form-item>
              <div class="matter-form-actions">
                <el-button @click="resetForm">重置</el-button>
                <el-button type="primary" :loading="submitting" :disabled="!canWriteCustomer" @click="submitMatter">保存事项</el-button>
              </div>
            </el-form>
            </div>
          </div>
        </template>
      </el-card>
    </section>
  </section>
</template>

<style scoped>
.customer-matters-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.matter-head-card,
.matter-summary-card,
.matter-detail-card {
  border-color: #dfe6e8;
}

.matter-head,
.matter-section-head,
.matter-item-head,
.matter-item-actions,
.matter-form-actions,
.matter-detail-topline,
.matter-summary-actions,
.matter-detail-header-actions {
  display: flex;
  gap: 10px;
}

.matter-head,
.matter-item-head {
  justify-content: space-between;
  align-items: flex-start;
}

.matter-section-head {
  align-items: flex-start;
}

.matter-summary-head {
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
}

.matter-detail-head {
  align-items: flex-start;
}

.matter-section-copy-block {
  min-width: 0;
}

.matter-title,
.matter-section-title {
  font-size: 16px;
  font-weight: 700;
  color: #172330;
}

.matter-copy,
.matter-section-copy,
.matter-empty-copy,
.matter-item-subtitle,
.matter-item-meta {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: #667085;
}

.matter-summary-actions,
.matter-detail-header-actions {
  align-items: center;
  flex-wrap: wrap;
}

.matter-summary-actions {
  width: 100%;
  justify-content: flex-start;
}

.matter-summary-actions :deep(.el-input) {
  flex: 1 1 320px;
}

.matter-summary-actions :deep(.el-tag) {
  margin-left: auto;
}

.matter-workspace {
  display: grid;
  grid-template-columns: minmax(500px, 0.98fr) minmax(0, 1.02fr);
  gap: 12px;
}

.matter-summary-card :deep(.el-card__header),
.matter-detail-card :deep(.el-card__header) {
  padding-bottom: 12px;
}

.matter-summary-table :deep(.el-table__cell) {
  padding: 6px 0;
}

.matter-customer-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.matter-customer-cell span {
  font-size: 12px;
  color: #667085;
}

.matter-detail-body {
  min-height: 520px;
}

.matter-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.matter-item,
.matter-empty {
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fafbfc;
}

.matter-item-title,
.matter-empty-title {
  font-size: 14px;
  font-weight: 700;
  color: #111827;
}

.matter-item-content {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.6;
  color: #172330;
}

.matter-item-meta,
.matter-item-actions {
  margin-top: 8px;
  flex-wrap: wrap;
}

.matter-form {
  margin-top: 10px;
}

.wide-field {
  width: 100%;
}

@media (max-width: 960px) {
  .matter-workspace {
    grid-template-columns: 1fr;
  }

  .matter-head {
    flex-direction: column;
  }

  .matter-summary-actions {
    width: 100%;
  }

  .matter-summary-actions :deep(.el-tag) {
    margin-left: 0;
  }
}
</style>
