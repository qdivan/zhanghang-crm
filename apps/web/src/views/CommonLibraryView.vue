<script setup lang="ts">
import { Delete, Edit, Plus } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref, watch } from "vue";

import { apiClient } from "../api/client";
import { useResponsive } from "../composables/useResponsive";
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
const loading = ref(false);
const rows = ref<CommonLibraryItem[]>([]);
const keyword = ref("");
const activeTab = ref<CommonLibraryModuleType>("TEMPLATE");
const visibilityFilter = ref<LibraryVisibilityFilter>("ALL");
const showDialog = ref(false);

const moduleMetaMap: Record<CommonLibraryModuleType, ModuleMeta> = {
  TEMPLATE: {
    label: "常用模板",
    helper: "保存可以直接复制给客户的资料、话术和通知模板。",
    categoryLabel: "模板分类",
    titleLabel: "模板标题",
    contentLabel: "模板内容",
    showContent: true,
    showPhone: false,
    showAddress: false,
  },
  DIRECTORY: {
    label: "通讯录模板",
    helper: "整理税局、审批局、人社局、银行等常用联系方式。",
    categoryLabel: "机构分类",
    titleLabel: "单位/联系人",
    contentLabel: "补充说明",
    showContent: true,
    showPhone: true,
    showAddress: true,
  },
  EXTENSION_A: {
    label: "扩展模块1",
    helper: "预留给后续新增的常用语、资料清单或标准说明。",
    categoryLabel: "分类",
    titleLabel: "标题",
    contentLabel: "内容",
    showContent: true,
    showPhone: false,
    showAddress: false,
  },
  EXTENSION_B: {
    label: "扩展模块2",
    helper: "预留给后续扩展用途，当前可先作为常用语库使用。",
    categoryLabel: "分类",
    titleLabel: "标题",
    contentLabel: "内容",
    showContent: true,
    showPhone: false,
    showAddress: false,
  },
  EXTENSION_C: {
    label: "扩展模块3",
    helper: "预留模块，后续可以改成新的资料板块。",
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
  fetchItems();
});

onMounted(() => {
  resetForm();
  fetchItems();
});
</script>

<template>
  <el-space direction="vertical" fill :size="12">
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

  <el-dialog v-model="showDialog" :title="dialogTitle" :width="isMobile ? '94%' : '760px'">
    <el-form label-position="top">
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
      <el-button @click="showDialog = false">取消</el-button>
      <el-button type="primary" @click="submitForm">保存</el-button>
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

@media (max-width: 900px) {
  .filter-form {
    display: flex;
    flex-wrap: wrap;
  }
}
</style>
