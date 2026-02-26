<script setup lang="ts">
import { ElMessage } from "element-plus";
import { onMounted, reactive, ref } from "vue";

import { apiClient } from "../api/client";
import type { AddressResource } from "../types";

type ResourceForm = {
  id: number | null;
  category: string;
  contact_info: string;
  description: string;
  next_action: string;
  notes: string;
};

const loading = ref(false);
const rows = ref<AddressResource[]>([]);
const keyword = ref("");
const showDialog = ref(false);

const form = reactive<ResourceForm>({
  id: null,
  category: "",
  contact_info: "",
  description: "",
  next_action: "",
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
  } catch (error) {
    ElMessage.error("获取地址资源失败");
  } finally {
    loading.value = false;
  }
}

function resetForm() {
  form.id = null;
  form.category = "";
  form.contact_info = "";
  form.description = "";
  form.next_action = "";
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
  form.description = row.description;
  form.next_action = row.next_action;
  form.notes = row.notes;
  showDialog.value = true;
}

async function submitForm() {
  if (!form.category && !form.contact_info && !form.description) {
    ElMessage.warning("请至少填写分类、联系方式或资源说明");
    return;
  }
  try {
    if (form.id) {
      await apiClient.patch(`/address-resources/${form.id}`, {
        category: form.category,
        contact_info: form.contact_info,
        description: form.description,
        next_action: form.next_action,
        notes: form.notes,
      });
      ElMessage.success("地址资源已更新");
    } else {
      await apiClient.post("/address-resources", {
        category: form.category,
        contact_info: form.contact_info,
        description: form.description,
        next_action: form.next_action,
        notes: form.notes,
      });
      ElMessage.success("地址资源已新增");
    }
    showDialog.value = false;
    await fetchResources();
  } catch (error) {
    ElMessage.error("保存失败");
  }
}

onMounted(fetchResources);
</script>

<template>
  <el-space direction="vertical" fill :size="12">
    <el-card shadow="never">
      <el-form inline @submit.prevent="fetchResources">
        <el-form-item label="关键词">
          <el-input
            v-model="keyword"
            placeholder="分类/联系方式/说明"
            clearable
            @keyup.enter="fetchResources"
          />
        </el-form-item>
        <el-form-item>
          <el-button @click="fetchResources">查询</el-button>
          <el-button type="primary" @click="openCreateDialog">新增资源</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="head">
          <span>地址资源池（转化2026）</span>
          <el-tag type="success" effect="plain">{{ rows.length }} 条</el-tag>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe border>
        <el-table-column prop="category" label="分类/区域" width="160" />
        <el-table-column prop="contact_info" label="联系方式" min-width="220" />
        <el-table-column prop="description" label="资源说明" min-width="300" />
        <el-table-column prop="next_action" label="后续动作" min-width="220" />
        <el-table-column prop="notes" label="备注" min-width="200" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </el-space>

  <el-dialog v-model="showDialog" :title="form.id ? '编辑地址资源' : '新增地址资源'" width="760px">
    <el-form label-position="top">
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="分类/区域">
            <el-input v-model="form.category" />
          </el-form-item>
        </el-col>
        <el-col :span="16">
          <el-form-item label="联系方式">
            <el-input v-model="form.contact_info" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="资源说明">
        <el-input v-model="form.description" type="textarea" :rows="3" />
      </el-form-item>
      <el-form-item label="后续动作">
        <el-input v-model="form.next_action" />
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
}
</style>
