<script setup lang="ts">
import { ElMessage } from "element-plus";
import { onMounted, reactive, ref } from "vue";

import { apiClient } from "../api/client";
import { useResponsive } from "../composables/useResponsive";
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
const rows = ref<AddressResource[]>([]);
const keyword = ref("");
const showDialog = ref(false);

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
  <el-space direction="vertical" fill :size="12">
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

  <el-dialog v-model="showDialog" :title="form.id ? '编辑挂靠地址' : '新增挂靠地址'" :width="isMobile ? '94%' : '760px'">
    <el-form label-position="top">
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
      <el-button @click="showDialog = false">取消</el-button>
      <el-button type="primary" @click="submitForm">保存</el-button>
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

@media (max-width: 900px) {
  .resource-filter-form {
    display: flex;
    flex-wrap: wrap;
  }
}
</style>
