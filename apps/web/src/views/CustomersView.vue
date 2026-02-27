<script setup lang="ts">
import { ElMessage } from "element-plus";
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { apiClient } from "../api/client";
import type { CustomerListItem } from "../types";

const router = useRouter();
const loading = ref(false);
const keyword = ref("");
const rows = ref<CustomerListItem[]>([]);

function templateLabel(template: string) {
  return template === "FOLLOWUP" ? "客户跟进" : "转化";
}

async function fetchCustomers() {
  loading.value = true;
  try {
    const resp = await apiClient.get<CustomerListItem[]>("/customers", {
      params: {
        keyword: keyword.value || undefined,
      },
    });
    rows.value = resp.data;
  } catch (error) {
    ElMessage.error("获取客户列表失败");
  } finally {
    loading.value = false;
  }
}

function openCustomerDetail(row: CustomerListItem) {
  router.push(`/customers/${row.id}`);
}

function openLeadDetail(row: CustomerListItem) {
  router.push({
    path: `/leads/${row.source_lead_id}`,
    query: { from: "customers" },
  });
}

onMounted(fetchCustomers);
</script>

<template>
  <el-space direction="vertical" fill :size="12">
    <el-card shadow="never">
      <el-form inline @submit.prevent="fetchCustomers" class="customers-filter-form">
        <el-form-item label="关键词">
          <el-input
            v-model="keyword"
            placeholder="客户/联系人/电话/会计"
            clearable
            @keyup.enter="fetchCustomers"
          />
        </el-form-item>
        <el-form-item>
          <el-button @click="fetchCustomers">查询</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="head">
          <span>客户列表（已转化）</span>
          <el-tag type="success" effect="plain">{{ rows.length }} 条</el-tag>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe border>
        <el-table-column prop="id" label="客户ID" width="90" />
        <el-table-column label="客户名称" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <el-button link type="primary" @click="openCustomerDetail(row)">{{ row.name }}</el-button>
          </template>
        </el-table-column>
        <el-table-column
          prop="contact_name"
          label="联系人"
          width="110"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="phone"
          label="电话"
          width="130"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="accountant_username"
          label="会计"
          width="110"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          label="来源模板"
          width="95"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        >
          <template #default="{ row }">{{ templateLabel(row.source_template_type) }}</template>
        </el-table-column>
        <el-table-column
          prop="source_grade"
          label="等级"
          width="70"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="source_last_followup_date"
          label="最后跟进"
          width="110"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          prop="source_reminder_value"
          label="提醒值"
          width="90"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        />
        <el-table-column
          label="操作"
          width="150"
          class-name="mobile-hide"
          label-class-name="mobile-hide"
        >
          <template #default="{ row }">
            <el-space class="table-action-wrap">
              <el-button link type="primary" @click="openCustomerDetail(row)">客户档案</el-button>
              <el-button link @click="openLeadDetail(row)">线索详情</el-button>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </el-space>
</template>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

@media (max-width: 900px) {
  .customers-filter-form {
    display: flex;
    flex-wrap: wrap;
  }
}
</style>
