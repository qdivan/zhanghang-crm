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
const categoryOptions = computed(() => {
  const unique = new Set<string>();
  rows.value.forEach((item) => {
    const token = (item.category || "").trim();
    if (token) unique.add(token);
  });
  return Array.from(unique).sort((left, right) => left.localeCompare(right, "zh-CN"));
});
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
const selectedCategoryLabel = computed(() => {
  if (!selectedCategory.value) return "全部分类";
  if (selectedCategory.value === UNCATEGORIZED_CATEGORY) return "未分类";
  return selectedCategory.value;
});
const selectedCategoryHelper = computed(() => {
  if (!selectedCategory.value) {
    return `当前展示 ${activeMeta.value.label} 的全部条目，可以先从左侧分类切进去再处理。`;
  }
  if (selectedCategory.value === UNCATEGORIZED_CATEGORY) {
    return "这些条目还没归类，适合先整理分类，再让同事更快复用。";
  }
  return `当前只看“${selectedCategory.value}”分类，适合集中维护这一组资料。`;
});
const internalCount = computed(() => rows.value.filter((item) => item.visibility === "INTERNAL").length);
const publicCount = computed(() => rows.value.filter((item) => item.visibility === "PUBLIC").length);
const activeWorkspaceRow = computed(() => {
  if (!visibleRows.value.length) return null;
  return visibleRows.value.find((item) => item.id === desktopSelectedRowId.value) || visibleRows.value[0] || null;
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
  const expectedName = row.title || row.category || "该条资料";
  try {
    const result = (await ElMessageBox.prompt(
      `请输入“${expectedName}”确认删除这条资料。`,
      "删除确认",
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
  } catch {
    return;
  }

  try {
    await apiClient.delete(`/common-library-items/${row.id}`, {
      params: { confirm_name: expectedName },
    });
    ElMessage.success("已删除");
    await fetchItems();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || "删除失败");
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

function workspacePreviewContent(row: CommonLibraryItem) {
  if (row.module_type === "DIRECTORY") {
    return row.content || row.notes || "这条通讯录还没有补充说明。";
  }
  return row.content || row.notes || "这条资料还没有正文内容。";
}

function workspaceListHint(row: CommonLibraryItem) {
  if (row.module_type === "DIRECTORY") {
    return [row.phone, row.address].filter(Boolean).join(" · ") || "补充电话或地址后会显示在这里。";
  }
  return row.content || row.notes || "还没有填写内容。";
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
    return;
  }
  if (!items.some((item) => item.id === desktopSelectedRowId.value)) {
    desktopSelectedRowId.value = items[0].id;
  }
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

  <el-space v-else direction="vertical" fill :size="12">
    <el-card shadow="never" class="library-workspace-card">
      <template #header>
        <div class="page-head">
          <div>
            <div class="page-title">常用资料</div>
            <div class="page-desc">常用资料、通讯录和扩展模块统一沉淀，并区分内部资料与可公开到官网的内容。</div>
          </div>
          <el-tag type="info" effect="plain">{{ visibleRows.length }} 条</el-tag>
        </div>
      </template>

      <el-tabs v-model="activeTab" class="module-tabs">
        <el-tab-pane
          v-for="key in visibleModuleKeys"
          :key="key"
          :label="moduleMetaMap[key].label"
          :name="key"
        >
          <div class="tab-helper">{{ moduleMetaMap[key].helper }}</div>
        </el-tab-pane>
      </el-tabs>

      <div class="library-workspace">
        <aside class="library-sidebar">
          <section class="library-sidebar-panel">
            <div class="library-sidebar-title">分类工作台</div>
            <div class="library-sidebar-copy">先按分类聚焦，再在右侧处理条目，日常查资料会更快。</div>
            <div class="library-sidebar-metrics">
              <article class="library-sidebar-metric">
                <span>全部条目</span>
                <strong>{{ rows.length }}</strong>
              </article>
              <article class="library-sidebar-metric">
                <span>内部资料</span>
                <strong>{{ internalCount }}</strong>
              </article>
              <article class="library-sidebar-metric">
                <span>可公开</span>
                <strong>{{ publicCount }}</strong>
              </article>
            </div>
          </section>

          <section class="library-sidebar-panel">
            <div class="library-sidebar-section-head">
              <div>
                <div class="library-sidebar-title">{{ activeMeta.categoryLabel }}</div>
                <div class="library-sidebar-copy">点左侧分类后，右侧只看这一类内容。</div>
              </div>
              <el-tag size="small" effect="plain">{{ categoryWorkspaceOptions.length - 1 }} 类</el-tag>
            </div>
            <div class="library-category-list">
              <button
                v-for="item in categoryWorkspaceOptions"
                :key="`library-category-workspace-${item.key || 'all'}`"
                type="button"
                class="library-category-button"
                :class="{ active: selectedCategory === item.key }"
                @click="selectedCategory = item.key"
              >
                <span>{{ item.label }}</span>
                <strong>{{ item.count }}</strong>
              </button>
            </div>
          </section>
        </aside>

        <section class="library-main-panel">
          <div class="library-main-toolbar">
            <el-form class="library-filter-form" @submit.prevent="fetchItems">
              <div class="library-filter-grid">
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
                    <el-radio-button value="ALL">全部</el-radio-button>
                    <el-radio-button value="INTERNAL">内部资料</el-radio-button>
                    <el-radio-button value="PUBLIC">可公开到官网</el-radio-button>
                  </el-radio-group>
                </el-form-item>
                <el-form-item label="分类切换">
                  <el-select
                    v-model="selectedCategory"
                    clearable
                    filterable
                    placeholder="全部分类"
                    class="library-category-select"
                  >
                    <el-option label="全部分类" value="" />
                    <el-option label="未分类" :value="UNCATEGORIZED_CATEGORY" />
                    <el-option
                      v-for="item in categoryOptions"
                      :key="`library-category-${item}`"
                      :label="item"
                      :value="item"
                    />
                  </el-select>
                </el-form-item>
              </div>
            </el-form>
            <div class="library-toolbar-actions">
              <el-button @click="fetchItems">查询</el-button>
              <el-button type="primary" :icon="Plus" @click="openCreateDialog()">新增</el-button>
            </div>
          </div>

          <div class="library-main-head">
            <div>
              <div class="library-main-title">{{ selectedCategoryLabel }}</div>
              <div class="library-main-copy">{{ selectedCategoryHelper }}</div>
            </div>
            <div class="library-main-head-actions">
              <el-tag type="info" effect="plain">{{ visibleRows.length }} 条</el-tag>
              <el-button size="small" plain :icon="Plus" @click="openCreateDialog()">
                当前分类新增
              </el-button>
            </div>
          </div>

          <div v-loading="loading" class="library-workbench">
            <div v-if="!visibleRows.length" class="library-empty-state">
              <div class="library-empty-kicker">{{ activeMeta.label }}</div>
              <div class="library-empty-title">当前分类还没有内容</div>
              <div class="library-empty-copy">可以先新增一条，或回到左侧切换其他分类继续查看。</div>
            </div>
            <template v-else>
              <section class="library-entry-list-panel">
                <div class="library-entry-list-head">
                  <div>
                    <div class="library-entry-list-title">条目列表</div>
                    <div class="library-entry-list-copy">左侧定分类，右侧先选条目，再看详情或直接编辑。</div>
                  </div>
                  <el-tag effect="plain">{{ visibleRows.length }}</el-tag>
                </div>
                <div class="library-entry-list">
                  <button
                    v-for="row in visibleRows"
                    :key="row.id"
                    type="button"
                    class="library-entry-button"
                    :class="{ active: activeWorkspaceRow?.id === row.id }"
                    @click="desktopSelectedRowId = row.id"
                  >
                    <div class="library-entry-button-head">
                      <div class="library-entry-button-title">{{ row.title || row.category || activeMeta.label }}</div>
                      <el-tag size="small" :type="visibilityTagType(row.visibility)" effect="plain">
                        {{ visibilityLabel(row.visibility) }}
                      </el-tag>
                    </div>
                    <div class="library-entry-button-meta">
                      <span>{{ row.category || "未分类" }}</span>
                      <span v-if="row.module_type === 'DIRECTORY' && row.phone">{{ row.phone }}</span>
                    </div>
                    <div class="library-entry-button-copy">{{ workspaceListHint(row) }}</div>
                  </button>
                </div>
              </section>

              <section v-if="activeWorkspaceRow" class="library-preview-panel">
                <div class="library-preview-head">
                  <div class="library-preview-main">
                    <div class="library-preview-title">{{ activeWorkspaceRow.title || activeMeta.label }}</div>
                    <div class="library-preview-meta">
                      <span>{{ activeWorkspaceRow.category || "未分类" }}</span>
                      <el-tag size="small" :type="visibilityTagType(activeWorkspaceRow.visibility)" effect="plain">
                        {{ visibilityLabel(activeWorkspaceRow.visibility) }}
                      </el-tag>
                    </div>
                  </div>
                  <div class="library-preview-actions">
                    <el-button size="small" plain @click="openEditDialog(activeWorkspaceRow)">编辑</el-button>
                    <el-button
                      v-if="canDelete"
                      size="small"
                      type="danger"
                      plain
                      @click="removeItem(activeWorkspaceRow)"
                    >
                      删除
                    </el-button>
                  </div>
                </div>

                <div class="library-preview-body">
                  <section class="library-preview-section">
                    <div class="library-preview-section-label">{{ activeMeta.contentLabel }}</div>
                    <div class="library-preview-richtext">{{ workspacePreviewContent(activeWorkspaceRow) }}</div>
                  </section>

                  <section v-if="activeWorkspaceRow.module_type === 'DIRECTORY'" class="library-preview-directory-grid">
                    <article class="library-preview-directory-card">
                      <span>电话</span>
                      <strong>{{ activeWorkspaceRow.phone || "-" }}</strong>
                    </article>
                    <article class="library-preview-directory-card">
                      <span>地址</span>
                      <strong>{{ activeWorkspaceRow.address || "-" }}</strong>
                    </article>
                  </section>

                  <section v-if="activeWorkspaceRow.notes" class="library-preview-section secondary">
                    <div class="library-preview-section-label">备注</div>
                    <div class="library-preview-note">{{ activeWorkspaceRow.notes }}</div>
                  </section>
                </div>
              </section>
            </template>
          </div>
        </section>
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

.library-workspace-card {
  border-color: #dfe6e8;
}

.library-workspace {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 16px;
  margin-top: 8px;
}

.library-sidebar,
.library-main-panel {
  min-width: 0;
}

.library-sidebar {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.library-sidebar-panel,
.library-main-toolbar,
.library-main-head,
.library-item-card,
.library-empty-state {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fafbfc;
}

.library-sidebar-panel,
.library-main-toolbar,
.library-main-head,
.library-empty-state {
  padding: 14px;
}

.library-sidebar-title,
.library-main-title,
.library-item-card-title {
  font-size: 15px;
  font-weight: 700;
  color: #111827;
}

.library-sidebar-copy,
.library-main-copy,
.library-item-card-note {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: #6b7280;
}

.library-sidebar-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 12px;
}

.library-sidebar-metric {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px;
  border: 1px solid #e3e8ef;
  border-radius: 10px;
  background: #ffffff;
}

.library-sidebar-metric span,
.library-category-button span,
.library-directory-meta-item span {
  font-size: 11px;
  color: #6b7280;
}

.library-sidebar-metric strong,
.library-category-button strong,
.library-directory-meta-item strong {
  font-size: 13px;
  color: #111827;
}

.library-sidebar-section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.library-category-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
  max-height: 520px;
  overflow: auto;
}

.library-category-button {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  padding: 11px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #ffffff;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    background-color 0.2s ease,
    transform 0.2s ease;
}

.library-category-button:hover {
  border-color: #cbd5e1;
  transform: translateY(-1px);
}

.library-category-button.active {
  border-color: #8fb2be;
  background: rgba(143, 178, 190, 0.12);
}

.library-main-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.library-main-toolbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.library-filter-form {
  flex: 1;
}

.library-filter-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.library-filter-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.library-filter-form :deep(.el-select__wrapper),
.library-filter-form :deep(.el-input__wrapper) {
  min-width: 200px;
}

.library-category-select {
  width: 100%;
}

.library-toolbar-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.library-main-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.library-main-head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.library-workbench {
  display: grid;
  grid-template-columns: minmax(280px, 0.95fr) minmax(0, 1.35fr);
  gap: 12px;
}

.library-entry-list-panel,
.library-preview-panel {
  min-width: 0;
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fafbfc;
}

.library-entry-list-head,
.library-preview-head,
.library-preview-meta,
.library-preview-actions {
  display: flex;
  gap: 10px;
}

.library-entry-list-head,
.library-preview-head {
  align-items: flex-start;
  justify-content: space-between;
}

.library-entry-list-title,
.library-preview-title {
  font-size: 14px;
  font-weight: 700;
  color: #111827;
}

.library-entry-list-copy {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: #6b7280;
}

.library-entry-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
  max-height: 520px;
  overflow: auto;
}

.library-entry-button {
  width: 100%;
  padding: 11px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #ffffff;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    background-color 0.2s ease,
    transform 0.2s ease;
}

.library-entry-button:hover {
  border-color: #cbd5e1;
  transform: translateY(-1px);
}

.library-entry-button.active {
  border-color: #8fb2be;
  background: rgba(143, 178, 190, 0.12);
}

.library-entry-button-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.library-entry-button-title,
.library-preview-title {
  font-size: 15px;
  font-weight: 700;
  color: #111827;
}

.library-entry-button-meta,
.library-preview-meta {
  flex-wrap: wrap;
  margin-top: 6px;
  font-size: 12px;
  color: #6b7280;
}

.library-entry-button-copy {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.6;
  color: #4b5563;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.library-preview-main {
  min-width: 0;
}

.library-preview-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 14px;
}

.library-preview-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  border: 1px solid #e3e8ef;
  border-radius: 10px;
  background: #ffffff;
}

.library-preview-section.secondary {
  background: #fdfefe;
}

.library-preview-section-label {
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #6b7280;
}

.library-preview-richtext,
.library-preview-note {
  font-size: 13px;
  line-height: 1.7;
  color: #1f2937;
  white-space: pre-wrap;
}

.library-preview-directory-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.library-preview-directory-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #ffffff;
}

.library-empty-state {
  display: flex;
  flex-direction: column;
  gap: 6px;
  grid-column: 1 / -1;
  align-items: flex-start;
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
  .library-workspace {
    grid-template-columns: 1fr;
  }

  .library-sidebar-metrics,
  .library-filter-grid,
  .library-preview-directory-grid,
  .library-workbench {
    grid-template-columns: 1fr;
  }

  .library-main-toolbar,
  .library-entry-list-head,
  .library-preview-head,
  .library-main-head,
  .library-toolbar-actions,
  .library-main-head-actions,
  .library-preview-actions {
    flex-direction: column;
    align-items: stretch;
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
