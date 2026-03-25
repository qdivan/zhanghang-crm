<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute } from "vue-router";

import { apiClient } from "../api/client";
import { useResponsive } from "../composables/useResponsive";
import { isMobileAppPath } from "../mobile/config";
import type { AddressResource } from "../types";

type ResourceForm = {
  id: number | null;
  category: string;
  contact_info: string;
  served_companies: string;
  description: string;
  notes: string;
};

const loading = ref(false);
const { isMobile } = useResponsive();
const route = useRoute();
const rows = ref<AddressResource[]>([]);
const keyword = ref("");
const showDialog = ref(false);
const isMobileWorkflow = computed(() => isMobileAppPath(route.path));
const dialogTitle = computed(() => (form.id ? "编辑挂靠地址" : "新增挂靠地址"));

const form = reactive<ResourceForm>({
  id: null,
  category: "",
  contact_info: "",
  served_companies: "",
  description: "",
  notes: "",
});

async function fetchResources() {
  loading.value = true;
  try {
    const resp = await apiClient.get<AddressResource[]>("/address-resources", {
      params: {
        keyword: keyword.value || undefined,
      },
    });
    rows.value = resp.data;
  } catch {
    ElMessage.error("获取挂靠地址失败");
  } finally {
    loading.value = false;
  }
}

function resetForm() {
  form.id = null;
  form.category = "";
  form.contact_info = "";
  form.served_companies = "";
  form.description = "";
  form.notes = "";
}

function openCreateDialog() {
  resetForm();
  showDialog.value = true;
}

function openEditDialog(row: AddressResource) {
  form.id = row.id;
  form.category = row.category;
  form.contact_info = row.contact_info;
  form.served_companies = row.served_companies;
  form.description = row.description;
  form.notes = row.notes;
  showDialog.value = true;
}

async function submitForm() {
  if (!form.category && !form.contact_info && !form.served_companies && !form.description) {
    ElMessage.warning("请至少填写分类、地址/联系人、已服务公司或说明");
    return;
  }
  try {
    const payload = {
      category: form.category,
      contact_info: form.contact_info,
      served_companies: form.served_companies,
      description: form.description,
      next_action: "",
      notes: form.notes,
    };
    if (form.id) {
      await apiClient.patch(`/address-resources/${form.id}`, payload);
      ElMessage.success("挂靠地址已更新");
    } else {
      await apiClient.post("/address-resources", payload);
      ElMessage.success("挂靠地址已新增");
    }
    showDialog.value = false;
    await fetchResources();
  } catch {
    ElMessage.error("保存失败");
  }
}

onMounted(fetchResources);
</script>

<template>
  <template v-if="isMobileWorkflow">
    <section class="mobile-page mobile-address-page">
      <section class="mobile-shell-panel">
        <div class="mobile-address-toolbar">
          <el-input
            v-model="keyword"
            placeholder="分类 / 联系人 / 服务公司 / 说明"
            clearable
            @keyup.enter="fetchResources"
          />
          <div class="mobile-address-toolbar-actions">
            <el-button @click="fetchResources">查询</el-button>
            <el-button type="primary" @click="openCreateDialog">新增地址</el-button>
          </div>
        </div>
        <div v-if="keyword" class="mobile-chip-row mobile-address-chip-row">
          <button type="button" class="mobile-chip-button" @click="keyword = ''; fetchResources()">
            <span>关键词：{{ keyword }}</span>
            <span class="mobile-chip-close">移除</span>
          </button>
        </div>
      </section>

      <section class="mobile-shell-panel">
        <div class="mobile-address-section-head">
          <div>
            <div class="mobile-address-section-title">挂靠地址</div>
            <div class="mobile-address-section-copy">联系人、服务公司和说明集中在这里。</div>
          </div>
          <el-tag type="success" effect="plain">{{ rows.length }} 条</el-tag>
        </div>

        <div v-if="!rows.length && !loading" class="mobile-empty-block">当前没有匹配地址资源</div>
        <div v-else v-loading="loading" class="mobile-address-list">
          <article v-for="row in rows" :key="row.id" class="mobile-address-row">
            <div class="mobile-address-row-top">
              <div>
                <div class="mobile-address-row-title">{{ row.category || "未分类地址" }}</div>
                <div class="mobile-address-row-subtitle">{{ row.contact_info || "未填地址 / 联系人" }}</div>
              </div>
              <el-button size="small" type="primary" plain @click="openEditDialog(row)">编辑</el-button>
            </div>
            <div class="mobile-address-row-grid">
              <div class="mobile-address-row-item">
                <span>已服务公司</span>
                <strong>{{ row.served_companies || "-" }}</strong>
              </div>
              <div class="mobile-address-row-item">
                <span>资源说明</span>
                <strong>{{ row.description || "-" }}</strong>
              </div>
            </div>
            <div v-if="row.notes" class="mobile-address-row-note">备注 {{ row.notes }}</div>
          </article>
        </div>
      </section>
    </section>
  </template>

  <el-space v-else direction="vertical" fill :size="12">
    <el-card shadow="never">
      <template #header>
        <div class="head">
          <div>
            <div class="page-title">挂靠地址</div>
            <div class="page-desc">这里单独记录帮客户对接的挂靠地址，以及已经服务了哪些公司。</div>
          </div>
          <el-tag type="info" effect="plain">补充模块</el-tag>
        </div>
      </template>
      <el-form inline @submit.prevent="fetchResources" class="resource-filter-form">
        <el-form-item label="关键词">
          <el-input
            v-model="keyword"
            placeholder="分类/地址联系人/服务公司/说明"
            clearable
            @keyup.enter="fetchResources"
          />
        </el-form-item>
        <el-form-item>
          <el-button @click="fetchResources">查询</el-button>
          <el-button type="primary" @click="openCreateDialog">新增地址</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="head">
          <span>{{ isMobile ? "挂靠地址" : "挂靠地址记录" }}</span>
          <el-tag type="success" effect="plain">{{ rows.length }} 条</el-tag>
        </div>
      </template>
      <div v-if="isMobile" v-loading="loading" class="mobile-record-list">
        <div v-for="row in rows" :key="row.id" class="mobile-record-card">
          <div class="mobile-record-head">
            <div class="mobile-record-main">
              <div class="mobile-record-title">{{ row.category || "未分类地址" }}</div>
              <div class="mobile-record-subtitle">{{ row.contact_info || "未填地址/联系人" }}</div>
            </div>
            <el-button size="small" type="primary" plain @click="openEditDialog(row)">编辑</el-button>
          </div>
          <div class="mobile-record-metrics">
            <div class="mobile-metric">
              <div class="mobile-metric-label">已服务公司</div>
              <div class="mobile-metric-value">{{ row.served_companies || "-" }}</div>
            </div>
            <div class="mobile-metric">
              <div class="mobile-metric-label">资源说明</div>
              <div class="mobile-metric-value">{{ row.description || "-" }}</div>
            </div>
          </div>
          <div v-if="row.notes" class="mobile-record-note">备注：{{ row.notes }}</div>
        </div>
      </div>
      <el-table v-else v-loading="loading" :data="rows" stripe border>
        <el-table-column prop="category" label="分类/区域" width="140" />
        <el-table-column prop="contact_info" label="挂靠地址/联系人" min-width="220" show-overflow-tooltip />
        <el-table-column prop="served_companies" label="已服务公司" min-width="220" show-overflow-tooltip />
        <el-table-column prop="description" label="资源说明" min-width="180" show-overflow-tooltip />
        <el-table-column prop="notes" label="备注" min-width="160" show-overflow-tooltip />
        <el-table-column label="操作" width="90">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
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
    :class="{ 'mobile-address-dialog': isMobileWorkflow }"
  >
    <template v-if="isMobileWorkflow">
      <div class="mobile-form-dialog">
        <div class="mobile-form-dialog-head">
          <div>
            <div class="mobile-form-dialog-eyebrow">挂靠地址</div>
            <div class="mobile-form-dialog-title">{{ form.id ? "编辑地址资源" : "新增地址资源" }}</div>
            <div class="mobile-form-dialog-copy">先记联系人和服务公司，再补充说明。</div>
          </div>
          <el-button text @click="showDialog = false">关闭</el-button>
        </div>

        <el-form label-position="top" class="mobile-form-dialog-form">
          <section class="mobile-form-section">
            <div class="mobile-form-section-title">基础信息</div>
            <el-form-item label="分类 / 区域">
              <el-input v-model="form.category" />
            </el-form-item>
            <el-form-item label="挂靠地址 / 联系人">
              <el-input v-model="form.contact_info" />
            </el-form-item>
          </section>

          <section class="mobile-form-section">
            <div class="mobile-form-section-title">服务范围</div>
            <div class="mobile-form-section-copy">多个公司名可用顿号、逗号或换行分隔。</div>
            <el-form-item label="已服务公司">
              <el-input v-model="form.served_companies" type="textarea" :rows="4" />
            </el-form-item>
          </section>

          <section class="mobile-form-section">
            <div class="mobile-form-section-title">资源说明</div>
            <el-form-item label="资源说明">
              <el-input v-model="form.description" type="textarea" :rows="6" />
            </el-form-item>
          </section>

          <section class="mobile-form-section">
            <div class="mobile-form-section-title">补充备注</div>
            <el-form-item label="备注">
              <el-input v-model="form.notes" type="textarea" :rows="5" />
            </el-form-item>
          </section>
        </el-form>
      </div>
    </template>

    <el-form v-else label-position="top">
      <el-row :gutter="12">
        <el-col :xs="24" :sm="8">
          <el-form-item label="分类/区域">
            <el-input v-model="form.category" />
          </el-form-item>
        </el-col>
        <el-col :xs="24" :sm="16">
          <el-form-item label="挂靠地址/联系人">
            <el-input v-model="form.contact_info" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="已服务公司">
        <el-input v-model="form.served_companies" placeholder="可填写多个公司名，用顿号或逗号分隔" />
      </el-form-item>
      <el-form-item label="资源说明">
        <el-input v-model="form.description" type="textarea" :rows="3" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.notes" type="textarea" :rows="2" />
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
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.page-title {
  font-size: 18px;
  font-weight: 700;
}

.page-desc {
  color: #667085;
  font-size: 13px;
}

@media (max-width: 768px) {
  .resource-filter-form {
    display: flex;
    flex-wrap: wrap;
  }
}

.mobile-address-page {
  gap: 12px;
}

.mobile-address-toolbar {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mobile-address-toolbar-actions {
  display: flex;
  gap: 8px;
}

.mobile-address-toolbar-actions :deep(.el-button) {
  flex: 1;
}

.mobile-address-chip-row {
  margin-top: 10px;
}

.mobile-address-section-head,
.mobile-address-row-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.mobile-address-section-title,
.mobile-address-row-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.mobile-address-section-copy,
.mobile-address-row-subtitle,
.mobile-address-row-note {
  font-size: 12px;
  line-height: 1.5;
  color: var(--app-text-muted);
}

.mobile-address-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mobile-address-row {
  padding: 12px;
  border: 1px solid var(--app-border-soft);
  background: var(--app-bg-soft);
}

.mobile-address-row-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
}

.mobile-address-row-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.mobile-address-row-item span {
  font-size: 11px;
  color: var(--app-text-muted);
}

.mobile-address-row-item strong {
  font-size: 13px;
  line-height: 1.5;
  color: var(--app-text-primary);
}

.mobile-address-row-note {
  margin-top: 8px;
}

:deep(.mobile-address-dialog .el-dialog__header) {
  display: none;
}

:deep(.mobile-address-dialog .el-dialog__body) {
  padding: 0;
}

:deep(.mobile-address-dialog .el-dialog__footer) {
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

.mobile-form-dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.mobile-form-dialog-footer.mobile :deep(.el-button) {
  flex: 1;
}
</style>
