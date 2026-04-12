<script setup lang="ts">
import { Filter, MoreFilled, Plus } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";

import { apiClient } from "../api/client";
import MobileActionSheet from "../components/mobile/MobileActionSheet.vue";
import MobileFilterSheet from "../components/mobile/MobileFilterSheet.vue";
import { useResponsive } from "../composables/useResponsive";
import { isMobileAppPath } from "../mobile/config";
import { useAuthStore } from "../stores/auth";
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

const UNCATEGORIZED_CATEGORY = "__UNCATEGORIZED__";

const { isMobile } = useResponsive();
const route = useRoute();
const auth = useAuthStore();
const loading = ref(false);
const libraryHydrated = ref(false);
const rows = ref<CommonLibraryItem[]>([]);
const keyword = ref("");
const activeTab = ref<CommonLibraryModuleType>("TEMPLATE");
const selectedCategory = ref("");
const visibilityFilter = ref<LibraryVisibilityFilter>("ALL");
const showDialog = ref(false);
const showMobileFilters = ref(false);
const showLibraryActionSheet = ref(false);
const selectedLibraryRow = ref<CommonLibraryItem | null>(null);
const desktopSelectedRowId = ref<number | null>(null);
const selectedRowIds = ref<number[]>([]);
const expandedRowIds = ref<number[]>([]);
const isMobileWorkflow = computed(() => isMobileAppPath(route.path));

const moduleMetaMap: Record<CommonLibraryModuleType, ModuleMeta> = {
  TEMPLATE: {
    label: "常用资料",
    helper: "先按分类沉淀常用话术、资料和发送给客户的固定文本。",
    categoryLabel: "资料分类",
    titleLabel: "资料标题",
    contentLabel: "资料内容",
    showContent: true,
    showPhone: false,
    showAddress: false,
  },
  DIRECTORY: {
    label: "通讯录",
    helper: "按机构分类维护税局、审批局、人社局、银行等常用电话。",
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
const visibleModuleKeys = computed<CommonLibraryModuleType[]>(() => ["TEMPLATE", "DIRECTORY", "EXTENSION_A", "EXTENSION_B"]);
const canDelete = computed(() => auth.user?.role === "OWNER" || auth.user?.role === "ADMIN");
const categoryWorkspaceOptions = computed(() => {
  const counts = new Map<string, number>();
  let uncategorizedCount = 0;
  rows.value.forEach((item) => {
    const token = (item.category || "").trim();
    if (token) {
      counts.set(token, (counts.get(token) || 0) + 1);
    } else {
      uncategorizedCount += 1;
    }
  });

  const items = Array.from(counts.entries())
    .sort((left, right) => left[0].localeCompare(right[0], "zh-CN"))
    .map(([label, count]) => ({
      key: label,
      label,
      count,
    }));

  if (uncategorizedCount) {
    items.push({
      key: UNCATEGORIZED_CATEGORY,
      label: "未分类",
      count: uncategorizedCount,
    });
  }

  return [{ key: "", label: "全部分类", count: rows.value.length }, ...items];
});
const visibleRows = computed(() => {
  if (!selectedCategory.value) return rows.value;
  if (selectedCategory.value === UNCATEGORIZED_CATEGORY) {
    return rows.value.filter((item) => !(item.category || "").trim());
  }
  return rows.value.filter((item) => (item.category || "").trim() === selectedCategory.value);
});
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
  const items = [
    { key: "edit", label: "编辑资料", description: "修改标题、内容和资料范围。" },
    canDelete.value ? { key: "delete", label: "删除资料", description: "删除当前资料条目。", danger: true } : null,
  ].filter(Boolean) as Array<{ key: string; label: string; description: string; danger?: boolean }>;
  return selectedLibraryRow.value ? items : [];
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

function openCreateDialog(category?: string) {
  resetForm();
  form.category = category ?? (selectedCategory.value === UNCATEGORIZED_CATEGORY ? "" : selectedCategory.value);
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
  if (!canDelete.value) {
    ElMessage.warning("只有老板和管理员可以删除资料");
    return;
  }
  try {
    await ElMessageBox.confirm(
      `确认删除这条资料吗？\n${row.title || row.category || "未命名资料"}`,
      "删除确认",
      {
        type: "warning",
        confirmButtonText: "确认删除",
        cancelButtonText: "取消",
      },
    );
  } catch {
    return;
  }

  try {
    await apiClient.delete(`/common-library-items/${row.id}`);
    ElMessage.success("已删除");
    selectedRowIds.value = selectedRowIds.value.filter((item) => item !== row.id);
    await fetchItems();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || "删除失败");
  }
}

async function copyItem(row: CommonLibraryItem) {
  const text = [row.title, row.content, row.phone, row.address, row.notes].filter(Boolean).join("\n");
  if (!text.trim()) {
    ElMessage.warning("这条资料还没有可复制的内容");
    return;
  }
  try {
    await navigator.clipboard.writeText(text);
    ElMessage.success("已复制到剪贴板");
  } catch {
    ElMessage.error("复制失败，请稍后再试");
  }
}

function toggleRowSelection(rowId: number) {
  if (selectedRowIds.value.includes(rowId)) {
    selectedRowIds.value = selectedRowIds.value.filter((item) => item !== rowId);
    return;
  }
  selectedRowIds.value = [...selectedRowIds.value, rowId];
}

const hasSelectedRows = computed(() => selectedRowIds.value.length > 0);

async function removeSelectedItems() {
  if (!canDelete.value || !selectedRowIds.value.length) return;
  try {
    await ElMessageBox.confirm(
      `确认批量删除已勾选的 ${selectedRowIds.value.length} 条资料吗？`,
      "批量删除资料",
      {
        type: "warning",
        confirmButtonText: "确认删除",
        cancelButtonText: "取消",
      },
    );
  } catch {
    return;
  }

  try {
    await Promise.all(selectedRowIds.value.map((id) => apiClient.delete(`/common-library-items/${id}`)));
    ElMessage.success(`已删除 ${selectedRowIds.value.length} 条资料`);
    selectedRowIds.value = [];
    await fetchItems();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || "批量删除失败");
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

function detailContent(row: CommonLibraryItem) {
  if (row.module_type === "DIRECTORY") {
    return row.content || row.notes || "暂无补充说明";
  }
  return row.content || row.notes || "暂无内容";
}

function workspaceListTitle(row: CommonLibraryItem) {
  const title = (row.title || "").trim();
  const category = (row.category || "").trim();
  if (title && category && title === category) return title;
  return title || category || activeMeta.value.label;
}

function rowMetaTokens(row: CommonLibraryItem) {
  return [
    row.category && row.category !== workspaceListTitle(row) ? row.category : "",
    row.module_type === "DIRECTORY" ? row.phone : "",
    row.module_type === "DIRECTORY" ? row.address : "",
  ].filter(Boolean);
}

function rowHasExtraNote(row: CommonLibraryItem) {
  return Boolean(row.notes && row.notes.trim() && row.notes.trim() !== detailContent(row).trim());
}

function rowNeedsExpand(row: CommonLibraryItem) {
  return detailContent(row).length > 150 || (row.notes?.length || 0) > 100;
}

function isRowExpanded(rowId: number) {
  return expandedRowIds.value.includes(rowId);
}

function toggleRowExpanded(rowId: number) {
  if (isRowExpanded(rowId)) {
    expandedRowIds.value = expandedRowIds.value.filter((item) => item !== rowId);
    return;
  }
  expandedRowIds.value = [...expandedRowIds.value, rowId];
}

function visibilityLabel(value: CommonLibraryVisibility) {
  return value === "PUBLIC" ? "可公开到官网" : "内部资料";
}

function visibilityTagType(value: CommonLibraryVisibility): "success" | "info" {
  return value === "PUBLIC" ? "success" : "info";
}

watch(activeTab, () => {
  keyword.value = "";
  selectedCategory.value = "";
  resetForm();
  fetchItems();
});

watch(rows, () => {
  if (
    selectedCategory.value &&
    selectedCategory.value !== UNCATEGORIZED_CATEGORY &&
    !rows.value.some((item) => (item.category || "").trim() === selectedCategory.value)
  ) {
    selectedCategory.value = "";
  }
  if (
    selectedCategory.value === UNCATEGORIZED_CATEGORY &&
    rows.value.every((item) => (item.category || "").trim())
  ) {
    selectedCategory.value = "";
  }
});

watch(visibleRows, (items) => {
  if (!items.length) {
    desktopSelectedRowId.value = null;
    selectedRowIds.value = [];
    expandedRowIds.value = [];
    return;
  }
  if (!items.some((item) => item.id === desktopSelectedRowId.value)) {
    desktopSelectedRowId.value = items[0].id;
  }
  selectedRowIds.value = selectedRowIds.value.filter((item) => items.some((row) => row.id === item));
  expandedRowIds.value = expandedRowIds.value.filter((item) => items.some((row) => row.id === item));
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
            v-for="key in visibleModuleKeys"
            :key="key"
            type="button"
            class="mobile-filter-preset"
            :class="{ active: activeTab === key }"
            @click="activeTab = key"
          >
            <span>{{ moduleMetaMap[key].label }}</span>
            <strong>{{ key === activeTab ? visibleRows.length : "" }}</strong>
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
          <el-tag v-else class="mobile-count-tag" effect="plain">{{ visibleRows.length }} 条</el-tag>
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
          <div v-else-if="!visibleRows.length" class="mobile-empty-block">
            <div class="mobile-empty-kicker">{{ activeMeta.label }}</div>
            <div class="mobile-empty-title">当前没有匹配资料</div>
            <div class="mobile-empty-copy">换个分类、关键词或范围，再继续定位要用的资料。</div>
          </div>
          <template v-else>
            <article v-for="row in visibleRows" :key="row.id" class="mobile-library-row">
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
            <el-radio-button value="ALL">全部</el-radio-button>
            <el-radio-button value="INTERNAL">内部资料</el-radio-button>
            <el-radio-button value="PUBLIC">可公开到官网</el-radio-button>
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

  <el-space v-else direction="vertical" fill :size="10" class="workspace-page">
    <el-card shadow="never" class="library-workspace-card workspace-surface">
      <div class="workspace-header library-page-header">
        <div class="workspace-title-block">
          <div class="workspace-title">常用资料</div>
          <div class="workspace-copy">直接按分类查看真实内容，复制、编辑、删除都在当前列表里完成。</div>
        </div>
        <div class="workspace-actions">
          <el-input
            v-model="keyword"
            class="library-toolbar-search"
            clearable
            placeholder="关键词搜索"
            @keyup.enter="fetchItems"
          />
          <el-button size="small" @click="fetchItems">查询</el-button>
          <el-button size="small" type="primary" :icon="Plus" @click="openCreateDialog()">新增</el-button>
          <el-tag type="info" effect="plain" class="workspace-subtle-tag">{{ visibleRows.length }} 条</el-tag>
        </div>
      </div>

      <div class="library-toolbar-strip">
        <el-tabs v-model="activeTab" class="module-tabs module-tabs-compact">
          <el-tab-pane
            v-for="key in visibleModuleKeys"
            :key="key"
            :label="moduleMetaMap[key].label"
            :name="key"
          />
        </el-tabs>
        <div class="library-toolbar-filters">
          <el-select v-model="visibilityFilter" class="library-visibility-select">
            <el-option label="全部范围" value="ALL" />
            <el-option label="内部资料" value="INTERNAL" />
            <el-option label="可公开到官网" value="PUBLIC" />
          </el-select>
        </div>
      </div>

      <div class="library-category-strip">
        <button
          v-for="item in categoryWorkspaceOptions"
          :key="`library-category-workspace-${item.key || 'all'}`"
          type="button"
          class="library-category-chip"
          :class="{ active: selectedCategory === item.key }"
          @click="selectedCategory = item.key"
        >
          <span>{{ item.label }}</span>
          <strong>{{ item.count }}</strong>
        </button>
      </div>

      <div v-if="canDelete && hasSelectedRows" class="library-bulk-strip">
        <span>已勾选 {{ selectedRowIds.length }} 条</span>
        <el-button size="small" type="danger" plain @click="removeSelectedItems">
          批量删除
        </el-button>
      </div>

      <div v-loading="loading" class="library-list-shell">
        <div v-if="!visibleRows.length" class="library-empty-state">
          <div class="library-empty-kicker">{{ activeMeta.label }}</div>
          <div class="library-empty-title">当前没有匹配内容</div>
          <div class="library-empty-copy">换个分类、关键词或资料范围后再继续查找。</div>
        </div>
        <div v-else class="library-inline-list">
          <article v-for="row in visibleRows" :key="row.id" class="library-inline-row">
            <div class="library-inline-row-head">
              <div class="library-inline-row-main">
                <div class="library-inline-row-title-line">
                  <el-checkbox
                    v-if="canDelete"
                    :model-value="selectedRowIds.includes(row.id)"
                    @change="toggleRowSelection(row.id)"
                  />
                  <div class="library-inline-row-title">{{ workspaceListTitle(row) }}</div>
                  <el-tag size="small" :type="visibilityTagType(row.visibility)" effect="plain">
                    {{ visibilityLabel(row.visibility) }}
                  </el-tag>
                </div>
                <div v-if="rowMetaTokens(row).length" class="library-inline-row-meta">
                  <span v-for="token in rowMetaTokens(row)" :key="`${row.id}-${token}`">{{ token }}</span>
                </div>
              </div>
              <div class="library-inline-row-actions">
                <el-button link type="primary" @click="copyItem(row)">复制</el-button>
                <el-button link @click="openEditDialog(row)">编辑</el-button>
                <el-button
                  v-if="rowNeedsExpand(row)"
                  link
                  type="info"
                  @click="toggleRowExpanded(row.id)"
                >
                  {{ isRowExpanded(row.id) ? "收起" : "展开" }}
                </el-button>
                <el-button v-if="canDelete" link type="danger" @click="removeItem(row)">删除</el-button>
              </div>
            </div>

            <div
              class="library-inline-row-body"
              :class="{ collapsed: rowNeedsExpand(row) && !isRowExpanded(row.id) }"
            >
              {{ detailContent(row) }}
            </div>
            <div v-if="rowHasExtraNote(row)" class="library-inline-row-note">备注：{{ row.notes }}</div>
          </article>
        </div>
      </div>
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
                <el-radio-button value="INTERNAL">内部资料</el-radio-button>
                <el-radio-button value="PUBLIC">可公开到官网</el-radio-button>
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
              <el-radio-button value="INTERNAL">内部资料</el-radio-button>
              <el-radio-button value="PUBLIC">可公开到官网</el-radio-button>
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
.library-workspace-card {
  border-color: #dfe6e8;
}

.library-page-header {
  margin-bottom: 10px;
}

.library-toolbar-search {
  width: clamp(220px, 24vw, 320px);
}

.library-toolbar-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px 14px;
  margin-bottom: 10px;
  min-width: 0;
}

.module-tabs {
  min-width: 0;
  flex: 1;
}

.module-tabs-compact :deep(.el-tabs__header) {
  margin-bottom: 0;
}

.module-tabs-compact :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.library-toolbar-filters {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.library-category-select,
.library-visibility-select {
  min-width: 170px;
}

.library-category-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.library-category-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 11px;
  border: 1px solid #dfe5e8;
  border-radius: 999px;
  background: #fff;
  font-size: 12px;
  color: #51616d;
}

.library-category-chip strong {
  font-size: 11px;
  color: #172330;
}

.library-category-chip.active {
  border-color: #8fb2be;
  background: rgba(143, 178, 190, 0.1);
  color: #2f6073;
}

.library-bulk-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
  padding: 8px 12px;
  border: 1px dashed #d7dfe3;
  border-radius: 12px;
  background: #fbfcfc;
  font-size: 12px;
  color: #52616b;
}

.library-list-shell {
  min-width: 0;
}

.library-inline-list {
  display: flex;
  flex-direction: column;
}

.library-inline-row {
  padding: 12px 0;
  border-top: 1px solid #edf1f3;
}

.library-inline-row:first-child {
  padding-top: 0;
  border-top: none;
}

.library-inline-row-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px 16px;
}

.library-inline-row-main {
  min-width: 0;
  flex: 1;
}

.library-inline-row-title-line {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px 8px;
}

.library-inline-row-title {
  font-size: 14px;
  font-weight: 700;
  color: #172330;
}

.library-inline-row-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 10px;
  margin-top: 5px;
  font-size: 12px;
  color: #6b7280;
}

.library-inline-row-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 4px 8px;
  flex-shrink: 0;
}

.library-inline-row-body {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.68;
  color: #24323d;
  white-space: pre-wrap;
  word-break: break-word;
}

.library-inline-row-body.collapsed {
  display: -webkit-box;
  overflow: hidden;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

.library-inline-row-note {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.55;
  color: #6b7280;
}

.library-empty-state {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-start;
  padding: 18px 0 8px;
}

.library-empty-kicker {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #6b7280;
}

.library-empty-title {
  font-size: 18px;
  font-weight: 700;
  color: #111827;
}

.library-empty-copy {
  font-size: 13px;
  line-height: 1.6;
  color: #4b5563;
}

.mobile-actions {
  display: flex;
  gap: 8px;
}

@media (max-width: 768px) {
  .library-toolbar-strip,
  .library-inline-row-head {
    flex-direction: column;
    align-items: stretch;
  }

  .library-toolbar-search {
    width: 100%;
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
