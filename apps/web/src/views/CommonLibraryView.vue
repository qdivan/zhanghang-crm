<script setup lang="ts">
import { Delete, Edit, Filter, MoreFilled, Plus } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";

import { apiClient } from "../api/client";
import MobileActionSheet from "../components/mobile/MobileActionSheet.vue";
import MobileFilterSheet from "../components/mobile/MobileFilterSheet.vue";
import { useResponsive } from "../composables/useResponsive";
import { isMobileAppPath } from "../mobile/config";
import type { CommonLibraryItem, CommonLibraryModuleType, CommonLibraryVisibility } from "../types";

type LibraryForm = {
  id: number | null;
  module_type: CommonLibraryModuleType;
  visibility: CommonLibraryVisibility;
  category: string;
  title: string;
  content: string;
  phone: string;
  address: string;
  notes: string;
};

type LibraryVisibilityFilter = "ALL" | CommonLibraryVisibility;

type ModuleMeta = {
  label: string;
  helper: string;
  categoryLabel: string;
  titleLabel: string;
  contentLabel: string;
  showContent: boolean;
  showPhone: boolean;
  showAddress: boolean;
};

const { isMobile } = useResponsive();
const route = useRoute();
const loading = ref(false);
const libraryHydrated = ref(false);
const rows = ref<CommonLibraryItem[]>([]);
const keyword = ref("");
const activeTab = ref<CommonLibraryModuleType>("TEMPLATE");
const visibilityFilter = ref<LibraryVisibilityFilter>("ALL");
const showDialog = ref(false);
const showMobileFilters = ref(false);
const showLibraryActionSheet = ref(false);
const selectedLibraryRow = ref<CommonLibraryItem | null>(null);
const isMobileWorkflow = computed(() => isMobileAppPath(route.path));

const moduleMetaMap: Record<CommonLibraryModuleType, ModuleMeta> = {
  TEMPLATE: {
    label: "常用模板",
    helper: "沉淀可直接发给客户的模板和话术。",
    categoryLabel: "模板分类",
    titleLabel: "模板标题",
    contentLabel: "模板内容",
    showContent: true,
    showPhone: false,
    showAddress: false,
  },
  DIRECTORY: {
    label: "通讯录模板",
    helper: "沉淀税局、银行等常用联系人。",
    categoryLabel: "机构分类",
    titleLabel: "单位/联系人",
    contentLabel: "补充说明",
    showContent: true,
    showPhone: true,
    showAddress: true,
  },
  EXTENSION_A: {
    label: "扩展模块1",
    helper: "预留模块，可先放常用语或资料清单。",
    categoryLabel: "分类",
    titleLabel: "标题",
    contentLabel: "内容",
    showContent: true,
    showPhone: false,
    showAddress: false,
  },
  EXTENSION_B: {
    label: "扩展模块2",
    helper: "预留模块，可先放说明和常用语。",
    categoryLabel: "分类",
    titleLabel: "标题",
    contentLabel: "内容",
    showContent: true,
    showPhone: false,
    showAddress: false,
  },
  EXTENSION_C: {
    label: "扩展模块3",
    helper: "预留模块，后续按需改造。",
    categoryLabel: "分类",
    titleLabel: "标题",
    contentLabel: "内容",
    showContent: true,
    showPhone: false,
    showAddress: false,
  },
};

const activeMeta = computed(() => moduleMetaMap[activeTab.value]);
const dialogTitle = computed(() => (form.id ? `编辑${activeMeta.value.label}` : `新增${activeMeta.value.label}`));
const libraryFilterChips = computed(() =>
  [
    keyword.value ? { key: "keyword" as const, label: `关键词：${keyword.value}` } : null,
    visibilityFilter.value !== "ALL"
      ? { key: "visibility" as const, label: visibilityLabel(visibilityFilter.value as CommonLibraryVisibility) }
      : null,
  ].filter(Boolean) as Array<{ key: "keyword" | "visibility"; label: string }>,
);
const activeFilterChips = computed(() => libraryFilterChips.value.map((item) => item.label));
const showLibraryInitialSkeleton = computed(() => !libraryHydrated.value);
const libraryRowActionItems = computed(() => {
  if (!selectedLibraryRow.value) return [];
  return [
    { key: "edit", label: "编辑资料", description: "修改标题、内容和资料范围。" },
    { key: "delete", label: "删除资料", description: "删除当前资料条目。", danger: true },
  ];
});

const form = reactive<LibraryForm>({
  id: null,
  module_type: "TEMPLATE",
  visibility: "INTERNAL",
  category: "",
  title: "",
  content: "",
  phone: "",
  address: "",
  notes: "",
});

function resetForm() {
  form.id = null;
  form.module_type = activeTab.value;
  form.visibility = "INTERNAL";
  form.category = "";
  form.title = "";
  form.content = "";
  form.phone = "";
  form.address = "";
  form.notes = "";
}

async function fetchItems() {
  loading.value = true;
  try {
    const resp = await apiClient.get<CommonLibraryItem[]>("/common-library-items", {
      params: {
        module_type: activeTab.value,
        visibility: visibilityFilter.value === "ALL" ? undefined : visibilityFilter.value,
        keyword: keyword.value || undefined,
      },
    });
    rows.value = resp.data;
  } catch {
    ElMessage.error("获取常用资料失败");
  } finally {
    loading.value = false;
    libraryHydrated.value = true;
  }
}

function openCreateDialog() {
  resetForm();
  showDialog.value = true;
}

function openEditDialog(row: CommonLibraryItem) {
  form.id = row.id;
  form.module_type = row.module_type;
  form.visibility = row.visibility;
  form.category = row.category;
  form.title = row.title;
  form.content = row.content;
  form.phone = row.phone;
  form.address = row.address;
  form.notes = row.notes;
  showDialog.value = true;
}

function openLibraryRowActions(row: CommonLibraryItem) {
  selectedLibraryRow.value = row;
  showLibraryActionSheet.value = true;
}

async function submitForm() {
  const payload = {
    module_type: form.module_type,
    visibility: form.visibility,
    category: form.category,
    title: form.title,
    content: form.content,
    phone: form.phone,
    address: form.address,
    notes: form.notes,
  };
  try {
    if (form.id) {
      await apiClient.patch(`/common-library-items/${form.id}`, payload);
      ElMessage.success(`${activeMeta.value.label}已更新`);
    } else {
      await apiClient.post("/common-library-items", payload);
      ElMessage.success(`${activeMeta.value.label}已新增`);
    }
    showDialog.value = false;
    await fetchItems();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || "保存失败");
  }
}

async function removeItem(row: CommonLibraryItem) {
  try {
    await ElMessageBox.confirm(`确认删除“${row.title || row.category || "该条资料"}”？`, "删除确认", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }

  try {
    await apiClient.delete(`/common-library-items/${row.id}`);
    ElMessage.success("已删除");
    await fetchItems();
  } catch {
    ElMessage.error("删除失败");
  }
}

async function handleLibraryActionSelect(action: string) {
  if (!selectedLibraryRow.value) return;
  if (action === "edit") {
    openEditDialog(selectedLibraryRow.value);
    return;
  }
  if (action === "delete") {
    await removeItem(selectedLibraryRow.value);
  }
}

function primaryContent(row: CommonLibraryItem) {
  if (row.module_type === "DIRECTORY") {
    return [row.phone, row.address].filter(Boolean).join(" / ") || row.content || "-";
  }
  return row.content || row.notes || "-";
}

function visibilityLabel(value: CommonLibraryVisibility) {
  return value === "PUBLIC" ? "可公开到官网" : "内部资料";
}

function visibilityTagType(value: CommonLibraryVisibility): "success" | "info" {
  return value === "PUBLIC" ? "success" : "info";
}

watch(activeTab, () => {
  keyword.value = "";
  resetForm();
  fetchItems();
});

watch(visibilityFilter, () => {
  if (isMobileWorkflow.value) return;
  fetchItems();
});

function applyMobileFilters() {
  showMobileFilters.value = false;
  fetchItems();
}

function resetMobileFilters() {
  keyword.value = "";
  visibilityFilter.value = "ALL";
  applyMobileFilters();
}

function removeLibraryFilterChip(key: "keyword" | "visibility") {
  if (key === "keyword") keyword.value = "";
  if (key === "visibility") visibilityFilter.value = "ALL";
  fetchItems();
}

onMounted(() => {
  resetForm();
  fetchItems();
});
</script>

<template>
  <template v-if="isMobileWorkflow">
    <section class="mobile-page mobile-library-page">
      <section class="mobile-shell-panel">
        <div class="mobile-filter-presets mobile-library-tabs">
          <button
            v-for="(meta, key) in moduleMetaMap"
            :key="key"
            type="button"
            class="mobile-filter-preset"
            :class="{ active: activeTab === key }"
            @click="activeTab = key as CommonLibraryModuleType"
          >
            <span>{{ meta.label }}</span>
            <strong>{{ key === activeTab ? rows.length : "" }}</strong>
          </button>
        </div>
        <div class="mobile-library-helper">{{ activeMeta.helper }}</div>
        <div class="mobile-library-toolbar">
          <el-input
            v-model="keyword"
            clearable
            placeholder="分类 / 标题 / 电话 / 地址"
            @keyup.enter="fetchItems"
          />
          <div class="mobile-library-toolbar-actions">
            <el-button class="mobile-row-secondary-button" plain :icon="Filter" @click="showMobileFilters = true">
              筛选
            </el-button>
            <el-button class="mobile-row-primary-button" type="primary" :icon="Plus" @click="openCreateDialog">新增</el-button>
          </div>
        </div>
        <div v-if="activeFilterChips.length" class="mobile-chip-row mobile-library-chip-row">
          <button
            v-for="chip in libraryFilterChips"
            :key="chip.key"
            type="button"
            class="mobile-chip-button"
            @click="removeLibraryFilterChip(chip.key)"
          >
            <span>{{ chip.label }}</span>
            <span class="mobile-chip-close">移除</span>
          </button>
        </div>
      </section>

      <section class="mobile-shell-panel">
        <div class="mobile-library-section-head">
          <div>
            <div class="mobile-library-section-title">{{ activeMeta.label }}</div>
            <div class="mobile-library-section-copy">先筛范围，再处理资料。</div>
          </div>
          <div v-if="showLibraryInitialSkeleton" class="mobile-skeleton-chip mobile-library-count-skeleton"></div>
          <el-tag v-else class="mobile-count-tag" effect="plain">{{ rows.length }} 条</el-tag>
        </div>

        <div v-loading="loading && libraryHydrated" class="mobile-library-list">
          <template v-if="showLibraryInitialSkeleton">
            <article
              v-for="index in 4"
              :key="`library-skeleton-${index}`"
              class="mobile-library-row mobile-library-skeleton-row"
            >
              <div class="mobile-library-row-top">
                <div class="mobile-skeleton-stack mobile-library-skeleton-copy">
                  <div class="mobile-skeleton-line is-lg"></div>
                  <div class="mobile-skeleton-line is-sm"></div>
                </div>
                <div class="mobile-skeleton-button"></div>
              </div>
              <div class="mobile-skeleton-stack">
                <div class="mobile-skeleton-line is-full"></div>
                <div class="mobile-skeleton-line is-half"></div>
              </div>
              <div class="mobile-skeleton-line is-md"></div>
            </article>
          </template>
          <div v-else-if="!rows.length" class="mobile-empty-block">
            <div class="mobile-empty-kicker">{{ activeMeta.label }}</div>
            <div class="mobile-empty-title">当前没有匹配资料</div>
            <div class="mobile-empty-copy">换个分类、关键词或范围，再继续定位要用的资料。</div>
          </div>
          <template v-else>
            <article v-for="row in rows" :key="row.id" class="mobile-library-row">
              <div class="mobile-library-row-top">
                <div>
                  <div class="mobile-library-row-title">{{ row.title || row.category || activeMeta.label }}</div>
                  <div class="mobile-library-row-subtitle">{{ row.category || "未分类" }} · {{ visibilityLabel(row.visibility) }}</div>
                </div>
                <el-button class="mobile-row-secondary-button" size="small" plain @click="openLibraryRowActions(row)">
                  更多
                  <el-icon class="el-icon--right"><MoreFilled /></el-icon>
                </el-button>
              </div>
              <div class="mobile-library-row-body">{{ primaryContent(row) }}</div>
              <div v-if="row.notes" class="mobile-library-row-note">备注 {{ row.notes }}</div>
            </article>
          </template>
        </div>
      </section>
    </section>

    <MobileFilterSheet
      v-model="showMobileFilters"
      title="筛选资料"
      subtitle="先缩小范围，再看列表。"
      :summary-items="activeFilterChips"
      empty-summary="当前未设置筛选条件"
    >
      <el-form label-position="top" class="mobile-library-filter-form">
        <el-form-item label="关键词">
          <el-input
            v-model="keyword"
            clearable
            placeholder="分类 / 标题 / 内容 / 电话 / 地址"
            @keyup.enter="applyMobileFilters"
          />
        </el-form-item>
        <el-form-item label="资料范围">
          <el-radio-group v-model="visibilityFilter" class="mobile-library-radio-group">
            <el-radio-button label="ALL">全部</el-radio-button>
            <el-radio-button label="INTERNAL">内部资料</el-radio-button>
            <el-radio-button label="PUBLIC">可公开到官网</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetMobileFilters">重置</el-button>
        <el-button type="primary" @click="applyMobileFilters">应用筛选</el-button>
      </template>
    </MobileFilterSheet>

    <MobileActionSheet
      v-model="showLibraryActionSheet"
      title="资料操作"
      :subtitle="selectedLibraryRow?.title || selectedLibraryRow?.category || ''"
      :items="libraryRowActionItems"
      @select="handleLibraryActionSelect"
    />
  </template>

  <el-space v-else direction="vertical" fill :size="12">
    <el-card shadow="never">
      <template #header>
        <div class="page-head">
          <div>
            <div class="page-title">常用资料</div>
            <div class="page-desc">常用模板、通讯录、办事方法统一沉淀，并区分内部资料与可公开到官网的内容。</div>
          </div>
          <el-tag type="info" effect="plain">{{ rows.length }} 条</el-tag>
        </div>
      </template>

      <el-tabs v-model="activeTab" class="module-tabs">
        <el-tab-pane
          v-for="(meta, key) in moduleMetaMap"
          :key="key"
          :label="meta.label"
          :name="key"
        >
          <div class="tab-helper">{{ meta.helper }}</div>
        </el-tab-pane>
      </el-tabs>

      <el-form inline class="filter-form" @submit.prevent="fetchItems">
        <el-form-item label="关键词">
          <el-input
            v-model="keyword"
            clearable
            placeholder="分类/标题/内容/电话/地址"
            @keyup.enter="fetchItems"
          />
        </el-form-item>
        <el-form-item label="资料范围">
          <el-radio-group v-model="visibilityFilter">
            <el-radio-button label="ALL">全部</el-radio-button>
            <el-radio-button label="INTERNAL">内部资料</el-radio-button>
            <el-radio-button label="PUBLIC">可公开到官网</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <el-button @click="fetchItems">查询</el-button>
          <el-button type="primary" :icon="Plus" @click="openCreateDialog">新增</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <div v-if="isMobile" v-loading="loading" class="mobile-record-list">
        <div v-for="row in rows" :key="row.id" class="mobile-record-card">
          <div class="mobile-record-head">
            <div class="mobile-record-main">
              <div class="mobile-record-title">{{ row.title || row.category || activeMeta.label }}</div>
              <div class="mobile-record-subtitle">{{ row.category || "未分类" }} · {{ visibilityLabel(row.visibility) }}</div>
            </div>
            <div class="mobile-actions">
              <el-button size="small" plain @click="openEditDialog(row)">编辑</el-button>
              <el-button size="small" type="danger" plain @click="removeItem(row)">删除</el-button>
            </div>
          </div>
          <div class="mobile-metric">
            <div class="mobile-metric-label">主要内容</div>
            <div class="mobile-metric-value">{{ primaryContent(row) }}</div>
          </div>
          <div v-if="row.notes" class="mobile-record-note">备注：{{ row.notes }}</div>
        </div>
      </div>

      <el-table v-else v-loading="loading" :data="rows" stripe border>
        <el-table-column label="范围" width="130">
          <template #default="{ row }">
            <el-tag size="small" :type="visibilityTagType(row.visibility)" effect="plain">
              {{ visibilityLabel(row.visibility) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="140" />
        <el-table-column prop="title" :label="activeMeta.titleLabel" min-width="180" show-overflow-tooltip />
        <el-table-column label="主要内容" min-width="260" show-overflow-tooltip>
          <template #default="{ row }">
            {{ primaryContent(row) }}
          </template>
        </el-table-column>
        <el-table-column prop="notes" label="备注" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button link type="primary" :icon="Edit" @click="openEditDialog(row)">编辑</el-button>
            <el-button link type="danger" :icon="Delete" @click="removeItem(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </el-space>

  <el-dialog
    v-model="showDialog"
    :title="isMobileWorkflow ? '' : dialogTitle"
    :width="isMobile ? '94%' : '760px'"
    :fullscreen="isMobileWorkflow"
    :show-close="!isMobileWorkflow"
    :class="{ 'mobile-library-dialog': isMobileWorkflow }"
  >
    <template v-if="isMobileWorkflow">
      <div class="mobile-form-dialog">
        <div class="mobile-form-dialog-head">
          <div>
            <div class="mobile-form-dialog-eyebrow">{{ activeMeta.label }}</div>
            <div class="mobile-form-dialog-title">{{ form.id ? "编辑资料" : "新增资料" }}</div>
            <div class="mobile-form-dialog-copy">{{ activeMeta.helper }}</div>
          </div>
          <el-button text @click="showDialog = false">关闭</el-button>
        </div>

        <el-form label-position="top" class="mobile-form-dialog-form">
          <section class="mobile-form-section">
            <div class="mobile-form-section-title">资料范围</div>
            <div class="mobile-form-section-copy">先确认是否允许公开，再填内容。</div>
            <el-form-item label="资料范围">
              <el-radio-group v-model="form.visibility" class="mobile-form-radio-group">
                <el-radio-button label="INTERNAL">内部资料</el-radio-button>
                <el-radio-button label="PUBLIC">可公开到官网</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </section>

          <section class="mobile-form-section">
            <div class="mobile-form-section-title">基础信息</div>
            <el-form-item :label="activeMeta.categoryLabel">
              <el-input v-model="form.category" />
            </el-form-item>
            <el-form-item :label="activeMeta.titleLabel">
              <el-input v-model="form.title" />
            </el-form-item>
          </section>

          <section v-if="activeMeta.showPhone || activeMeta.showAddress" class="mobile-form-section">
            <div class="mobile-form-section-title">联系方式</div>
            <el-form-item v-if="activeMeta.showPhone" label="电话">
              <el-input v-model="form.phone" />
            </el-form-item>
            <el-form-item v-if="activeMeta.showAddress" label="地址">
              <el-input v-model="form.address" />
            </el-form-item>
          </section>

          <section v-if="activeMeta.showContent" class="mobile-form-section">
            <div class="mobile-form-section-title">{{ activeMeta.contentLabel }}</div>
            <el-form-item :label="activeMeta.contentLabel">
              <el-input v-model="form.content" type="textarea" :rows="8" />
            </el-form-item>
          </section>

          <section class="mobile-form-section">
            <div class="mobile-form-section-title">补充说明</div>
            <el-form-item label="备注">
              <el-input v-model="form.notes" type="textarea" :rows="5" />
            </el-form-item>
          </section>
        </el-form>
      </div>
    </template>

    <el-form v-else label-position="top">
      <el-row :gutter="12">
        <el-col :xs="24" :sm="12">
          <el-form-item label="资料范围">
            <el-radio-group v-model="form.visibility">
              <el-radio-button label="INTERNAL">内部资料</el-radio-button>
              <el-radio-button label="PUBLIC">可公开到官网</el-radio-button>
            </el-radio-group>
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="12">
        <el-col :xs="24" :sm="12">
          <el-form-item :label="activeMeta.categoryLabel">
            <el-input v-model="form.category" />
          </el-form-item>
        </el-col>
        <el-col :xs="24" :sm="12">
          <el-form-item :label="activeMeta.titleLabel">
            <el-input v-model="form.title" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row v-if="activeMeta.showPhone || activeMeta.showAddress" :gutter="12">
        <el-col v-if="activeMeta.showPhone" :xs="24" :sm="12">
          <el-form-item label="电话">
            <el-input v-model="form.phone" />
          </el-form-item>
        </el-col>
        <el-col v-if="activeMeta.showAddress" :xs="24" :sm="12">
          <el-form-item label="地址">
            <el-input v-model="form.address" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item v-if="activeMeta.showContent" :label="activeMeta.contentLabel">
        <el-input v-model="form.content" type="textarea" :rows="5" />
      </el-form-item>

      <el-form-item label="备注">
        <el-input v-model="form.notes" type="textarea" :rows="3" />
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="mobile-form-dialog-footer" :class="{ mobile: isMobileWorkflow }">
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="submitForm">保存</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.page-title {
  font-size: 18px;
  font-weight: 700;
}

.page-desc,
.tab-helper {
  color: #667085;
  font-size: 13px;
}

.filter-form {
  margin-top: 8px;
}

.mobile-actions {
  display: flex;
  gap: 8px;
}

@media (max-width: 768px) {
  .filter-form {
    display: flex;
    flex-wrap: wrap;
  }
}

.mobile-library-page {
  gap: 12px;
}

.mobile-library-tabs {
  margin-bottom: 10px;
}

.mobile-library-helper,
.mobile-library-section-copy,
.mobile-library-row-subtitle,
.mobile-library-row-note {
  font-size: 12px;
  line-height: 1.5;
  color: var(--app-text-muted);
}

.mobile-library-toolbar {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mobile-library-toolbar-actions {
  display: flex;
  gap: 8px;
}

.mobile-library-toolbar-actions :deep(.el-button) {
  flex: 1;
}

.mobile-library-chip-row {
  margin-top: 10px;
}

.mobile-library-section-head,
.mobile-library-row-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.mobile-library-section-title,
.mobile-library-row-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.mobile-library-count-skeleton {
  flex-shrink: 0;
}

.mobile-library-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mobile-library-row {
  padding: 12px;
  border: 1px solid var(--app-border-soft);
  background: var(--app-bg-soft);
}

.mobile-library-skeleton-row {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mobile-library-skeleton-copy {
  flex: 1;
}

.mobile-library-row-body {
  margin-top: 10px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--app-text-primary);
}

.mobile-library-row-note {
  margin-top: 8px;
}

.mobile-library-filter-form :deep(.el-form-item) {
  margin-bottom: 16px;
}

.mobile-library-radio-group {
  display: flex;
  flex-wrap: wrap;
}

:deep(.mobile-library-dialog .el-dialog__header) {
  display: none;
}

:deep(.mobile-library-dialog .el-dialog__body) {
  padding: 0;
}

:deep(.mobile-library-dialog .el-dialog__footer) {
  padding: 12px 16px calc(16px + env(safe-area-inset-bottom));
  border-top: 1px solid var(--app-border-soft);
}

.mobile-form-dialog {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 78px);
  background:
    radial-gradient(circle at top right, rgba(77, 128, 150, 0.12), transparent 34%),
    var(--app-bg);
}

.mobile-form-dialog-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: max(18px, env(safe-area-inset-top)) 16px 14px;
  border-bottom: 1px solid var(--app-border-soft);
  background: rgba(250, 252, 252, 0.94);
  backdrop-filter: blur(14px);
}

.mobile-form-dialog-eyebrow {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--app-text-muted);
}

.mobile-form-dialog-title {
  margin-top: 6px;
  font-size: 20px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.mobile-form-dialog-copy,
.mobile-form-section-copy {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--app-text-muted);
}

.mobile-form-dialog-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px 16px 24px;
}

.mobile-form-section {
  padding: 14px;
  border: 1px solid var(--app-border-soft);
  background: rgba(255, 255, 255, 0.92);
  box-shadow: var(--app-shadow-soft);
}

.mobile-form-section-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.mobile-form-section :deep(.el-form-item:last-child) {
  margin-bottom: 0;
}

.mobile-form-radio-group {
  display: flex;
  flex-wrap: wrap;
}

.mobile-form-dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.mobile-form-dialog-footer.mobile :deep(.el-button) {
  flex: 1;
}
</style>
