<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";

import { apiClient } from "../api/client";
import { useResponsive } from "../composables/useResponsive";
import { isMobileAppPath } from "../mobile/config";
import { useAuthStore } from "../stores/auth";
import type { AddressResource, AddressResourceCompanyItem, CustomerListItem } from "../types";

type ResourceForm = {
  id: number | null;
  category: string;
  contact_info: string;
  description: string;
  notes: string;
};

type CompanyForm = {
  customer_id: number | null;
  company_name: string;
  notes: string;
};

const loading = ref(false);
const resourcesHydrated = ref(false);
const { isMobile } = useResponsive();
const route = useRoute();
const auth = useAuthStore();
const rows = ref<AddressResource[]>([]);
const customers = ref<CustomerListItem[]>([]);
const keyword = ref("");
const showDialog = ref(false);
const showCompaniesDialog = ref(false);
const showAddCompanyDialog = ref(false);
const activeResource = ref<AddressResource | null>(null);
const isMobileWorkflow = computed(() => isMobileAppPath(route.path));
const dialogTitle = computed(() => (form.id ? "编辑挂靠地址" : "新增挂靠地址"));
const showAddressInitialSkeleton = computed(() => !resourcesHydrated.value);
const canDelete = computed(() => auth.user?.role === "OWNER" || auth.user?.role === "ADMIN");
const customerNameOptions = computed(() =>
  customers.value.map((item) => ({
    value: item.name,
    label: item.contact_name ? `${item.name} / ${item.contact_name}` : item.name,
  })),
);

const form = reactive<ResourceForm>({
  id: null,
  category: "",
  contact_info: "",
  description: "",
  notes: "",
});

const companyForm = reactive<CompanyForm>({
  customer_id: null,
  company_name: "",
  notes: "",
});

function resetForm() {
  form.id = null;
  form.category = "";
  form.contact_info = "";
  form.description = "";
  form.notes = "";
}

function resetCompanyForm() {
  companyForm.customer_id = null;
  companyForm.company_name = "";
  companyForm.notes = "";
}

function companyPreview(row: AddressResource) {
  return row.company_items.slice(0, 3).map((item) => item.company_name).join("、") || row.served_companies || "-";
}

async function fetchResources() {
  loading.value = true;
  try {
    const resp = await apiClient.get<AddressResource[]>("/address-resources", {
      params: {
        keyword: keyword.value || undefined,
      },
    });
    rows.value = resp.data;
    if (activeResource.value) {
      activeResource.value = resp.data.find((item) => item.id === activeResource.value?.id) || null;
    }
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "获取挂靠地址失败");
  } finally {
    loading.value = false;
    resourcesHydrated.value = true;
  }
}

async function fetchCustomers() {
  try {
    const resp = await apiClient.get<CustomerListItem[]>("/customers");
    customers.value = [...resp.data].sort((left, right) => left.name.localeCompare(right.name, "zh-CN"));
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "获取客户列表失败");
  }
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
  form.notes = row.notes;
  showDialog.value = true;
}

function openCompaniesDialog(row: AddressResource) {
  activeResource.value = row;
  showCompaniesDialog.value = true;
}

function openAddCompanyDialog(row: AddressResource) {
  activeResource.value = row;
  resetCompanyForm();
  showAddCompanyDialog.value = true;
}

async function submitForm() {
  if (!form.category.trim() && !form.contact_info.trim() && !form.description.trim()) {
    ElMessage.warning("请至少填写分类、地址/联系人或说明");
    return;
  }
  const payload = {
    category: form.category,
    contact_info: form.contact_info,
    description: form.description,
    next_action: "",
    notes: form.notes,
  };
  try {
    if (form.id) {
      await apiClient.patch(`/address-resources/${form.id}`, payload);
      ElMessage.success("挂靠地址已更新");
    } else {
      await apiClient.post("/address-resources", payload);
      ElMessage.success("挂靠地址已新增");
    }
    showDialog.value = false;
    await fetchResources();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "保存失败");
  }
}

async function submitCompanyForm() {
  if (!activeResource.value) return;
  const selectedCustomer = customers.value.find((item) => item.id === companyForm.customer_id) || null;
  const companyName = companyForm.company_name.trim() || selectedCustomer?.name || "";
  if (!companyName) {
    ElMessage.warning("请先选择客户或填写公司名称");
    return;
  }
  try {
    await apiClient.post(`/address-resources/${activeResource.value.id}/companies`, {
      customer_id: companyForm.customer_id,
      company_name: companyName,
      notes: companyForm.notes,
    });
    ElMessage.success("已服务公司已新增");
    showAddCompanyDialog.value = false;
    await fetchResources();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "新增失败");
  }
}

async function removeResource(row: AddressResource) {
  if (!canDelete.value) {
    ElMessage.warning("只有老板和管理员可以删除地址资源");
    return;
  }
  try {
    await ElMessageBox.confirm(
      `确认删除这条地址资源吗？\n${row.category || row.contact_info || `地址资源#${row.id}`}`,
      "删除地址资源",
      {
        type: "warning",
        confirmButtonText: "确认删除",
        cancelButtonText: "取消",
      },
    );
    await apiClient.delete(`/address-resources/${row.id}`);
    ElMessage.success("地址资源已删除");
    if (activeResource.value?.id === row.id) {
      showCompaniesDialog.value = false;
      activeResource.value = null;
    }
    await fetchResources();
  } catch (error: any) {
    if (error === "cancel" || error?.message === "cancel") return;
    ElMessage.error(error?.response?.data?.detail ?? "删除失败");
  }
}

async function removeCompany(item: AddressResourceCompanyItem) {
  if (!activeResource.value) return;
  if (!canDelete.value) {
    ElMessage.warning("只有老板和管理员可以删除已服务公司记录");
    return;
  }
  try {
    await ElMessageBox.confirm(
      `确认删除这条已服务公司记录吗？\n${item.company_name || item.customer_name || `公司记录#${item.id}`}`,
      "删除已服务公司",
      {
        type: "warning",
        confirmButtonText: "确认删除",
        cancelButtonText: "取消",
      },
    );
    await apiClient.delete(`/address-resources/${activeResource.value.id}/companies/${item.id}`);
    ElMessage.success("已服务公司记录已删除");
    await fetchResources();
  } catch (error: any) {
    if (error === "cancel" || error?.message === "cancel") return;
    ElMessage.error(error?.response?.data?.detail ?? "删除失败");
  }
}

onMounted(async () => {
  await Promise.all([fetchResources(), fetchCustomers()]);
});

watch(
  () => companyForm.customer_id,
  (value) => {
    const selectedCustomer = customers.value.find((item) => item.id === value) || null;
    if (selectedCustomer && !companyForm.company_name.trim()) {
      companyForm.company_name = selectedCustomer.name;
    }
  },
);

function fetchCompanyNameSuggestions(queryString: string, callback: (items: Array<{ value: string }>) => void) {
  const keywordValue = queryString.trim().toLowerCase();
  if (!keywordValue) {
    callback(customerNameOptions.value);
    return;
  }
  callback(customerNameOptions.value.filter((item) => item.value.toLowerCase().includes(keywordValue)));
}
</script>

<template>
  <template v-if="isMobileWorkflow">
    <section class="mobile-page mobile-address-page">
      <section class="mobile-shell-panel">
        <div class="mobile-address-toolbar">
          <el-input
            v-model="keyword"
            placeholder="分类 / 联系人 / 公司 / 说明"
            clearable
            @keyup.enter="fetchResources"
          />
          <div class="mobile-address-toolbar-actions">
            <el-button class="mobile-row-secondary-button" @click="fetchResources">查询</el-button>
            <el-button class="mobile-row-primary-button" type="primary" @click="openCreateDialog">新增地址</el-button>
          </div>
        </div>
      </section>

      <section class="mobile-shell-panel">
        <div class="mobile-address-section-head">
          <div>
            <div class="mobile-address-section-title">挂靠地址</div>
            <div class="mobile-address-section-copy">每条地址资源下面可以继续维护已服务公司。</div>
          </div>
          <el-tag v-if="!showAddressInitialSkeleton" class="mobile-count-tag" effect="plain">{{ rows.length }} 条</el-tag>
        </div>

        <div v-loading="loading && resourcesHydrated" class="mobile-address-list">
          <template v-if="showAddressInitialSkeleton">
            <article
              v-for="index in 4"
              :key="`address-skeleton-${index}`"
              class="mobile-address-row mobile-address-skeleton-row"
            >
              <div class="mobile-address-row-top">
                <div class="mobile-skeleton-stack mobile-address-skeleton-copy">
                  <div class="mobile-skeleton-line is-lg"></div>
                  <div class="mobile-skeleton-line is-sm"></div>
                </div>
                <div class="mobile-skeleton-button"></div>
              </div>
              <div class="mobile-address-row-grid">
                <div class="mobile-skeleton-line is-sm"></div>
                <div class="mobile-skeleton-line is-sm"></div>
              </div>
            </article>
          </template>
          <div v-else-if="!rows.length" class="mobile-empty-block">
            <div class="mobile-empty-kicker">挂靠地址</div>
            <div class="mobile-empty-title">当前没有匹配地址资源</div>
            <div class="mobile-empty-copy">换个关键词再查，或直接新增一条地址资源。</div>
          </div>
          <template v-else>
            <article v-for="row in rows" :key="row.id" class="mobile-address-row">
              <div class="mobile-address-row-top">
                <div>
                  <div class="mobile-address-row-title">{{ row.category || "未分类地址" }}</div>
                  <div class="mobile-address-row-subtitle">{{ row.contact_info || "未填地址 / 联系人" }}</div>
                </div>
                <el-button class="mobile-row-secondary-button" size="small" type="primary" plain @click="openEditDialog(row)">
                  编辑
                </el-button>
              </div>
              <div class="mobile-address-row-grid">
                <div class="mobile-address-row-item">
                  <span>已服务公司</span>
                  <strong>{{ row.served_company_count }} 家</strong>
                </div>
                <div class="mobile-address-row-item">
                  <span>资源说明</span>
                  <strong>{{ row.description || "-" }}</strong>
                </div>
              </div>
              <div class="mobile-address-row-note">{{ companyPreview(row) }}</div>
              <div class="mobile-address-actions">
                <el-button size="small" plain @click="openCompaniesDialog(row)">已服务的公司</el-button>
                <el-button size="small" type="primary" plain @click="openAddCompanyDialog(row)">增加</el-button>
                <el-button v-if="canDelete" size="small" type="danger" plain @click="removeResource(row)">删除</el-button>
              </div>
            </article>
          </template>
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
            <div class="page-desc">地址资源单独维护，下面再增加已服务的公司，方便查看每个地址正在服务哪些客户。</div>
          </div>
          <el-tag type="info" effect="plain">补充模块</el-tag>
        </div>
      </template>
      <el-form inline @submit.prevent="fetchResources" class="resource-filter-form">
        <el-form-item label="关键词">
          <el-input
            v-model="keyword"
            placeholder="分类 / 地址联系人 / 公司 / 说明"
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
      <el-table v-loading="loading" :data="rows" stripe border class="address-table">
        <el-table-column prop="category" label="分类" width="140" show-overflow-tooltip />
        <el-table-column prop="contact_info" label="地址 / 联系人" min-width="220" show-overflow-tooltip />
        <el-table-column prop="description" label="资源说明" min-width="220" show-overflow-tooltip />
        <el-table-column label="已服务的公司 / 增加" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="resource-company-cell">
              <div class="resource-company-preview">{{ companyPreview(row) }}</div>
              <div class="resource-company-actions">
                <el-button link type="primary" @click="openCompaniesDialog(row)">已服务的公司</el-button>
                <el-button link type="success" @click="openAddCompanyDialog(row)">增加</el-button>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="数量" width="88">
          <template #default="{ row }">{{ row.served_company_count }}</template>
        </el-table-column>
        <el-table-column prop="notes" label="备注" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <div class="resource-actions">
              <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
              <el-button v-if="canDelete" link type="danger" @click="removeResource(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </el-space>

  <el-dialog v-model="showDialog" :title="dialogTitle" :width="isMobile ? '94%' : '640px'">
    <el-form label-position="top">
      <el-row :gutter="12">
        <el-col :xs="24" :sm="12">
          <el-form-item label="分类">
            <el-input v-model="form.category" placeholder="如：注册地址 / 自贸区 / 银行地址" />
          </el-form-item>
        </el-col>
        <el-col :xs="24" :sm="12">
          <el-form-item label="地址 / 联系人">
            <el-input v-model="form.contact_info" placeholder="如：微信、电话、地址联系人" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="资源说明">
        <el-input v-model="form.description" type="textarea" :rows="4" placeholder="如：支持一般纳税人挂靠、报价口径、合作方式" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.notes" type="textarea" :rows="3" placeholder="补充说明或内部提醒" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showDialog = false">取消</el-button>
      <el-button type="primary" @click="submitForm">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="showCompaniesDialog" :title="`已服务的公司 - ${activeResource?.category || ''}`" :width="isMobile ? '96%' : '860px'">
    <template #header>
      <div class="company-dialog-head">
        <div>
          <div class="company-dialog-title">已服务的公司</div>
          <div class="company-dialog-copy">{{ activeResource?.contact_info || "可在这里查看这个地址资源已服务的公司" }}</div>
        </div>
        <el-button type="primary" plain @click="activeResource && openAddCompanyDialog(activeResource)">增加</el-button>
      </div>
    </template>
    <el-table :data="activeResource?.company_items || []" stripe border>
      <el-table-column prop="company_name" label="公司名称" min-width="180" show-overflow-tooltip />
      <el-table-column label="关联客户" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">{{ row.customer_name || "未关联客户档案" }}</template>
      </el-table-column>
      <el-table-column prop="notes" label="备注" min-width="220" show-overflow-tooltip />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button v-if="canDelete" link type="danger" @click="removeCompany(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-dialog>

  <el-dialog v-model="showAddCompanyDialog" :title="`增加已服务公司 - ${activeResource?.category || ''}`" :width="isMobile ? '94%' : '640px'">
    <el-form label-position="top">
      <el-form-item label="关联客户">
        <el-select
          v-model="companyForm.customer_id"
          class="wide-field"
          filterable
          clearable
          placeholder="可先搜索现有客户"
        >
          <el-option
            v-for="item in customers"
            :key="`address-company-customer-${item.id}`"
            :label="item.contact_name ? `${item.name} / ${item.contact_name}` : item.name"
            :value="item.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="公司名称">
        <el-autocomplete
          v-model="companyForm.company_name"
          class="wide-field"
          :fetch-suggestions="fetchCompanyNameSuggestions"
          placeholder="可联想已转化客户，也可手填未建档公司"
          clearable
        />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="companyForm.notes" type="textarea" :rows="3" placeholder="例如：挂靠期限、特殊约定、联系人" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showAddCompanyDialog = false">取消</el-button>
      <el-button type="primary" @click="submitCompanyForm">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.mobile-address-page {
  gap: 12px;
}

.mobile-address-toolbar {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mobile-address-toolbar-actions,
.mobile-address-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.mobile-address-toolbar-actions :deep(.el-button),
.mobile-address-actions :deep(.el-button) {
  flex: 1;
}

.mobile-address-section-head,
.mobile-address-row-top,
.head,
.company-dialog-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.mobile-address-section-title,
.page-title,
.company-dialog-title {
  font-size: 16px;
  font-weight: 700;
  color: #172330;
}

.mobile-address-section-copy,
.page-desc,
.company-dialog-copy,
.mobile-address-row-subtitle,
.mobile-address-row-note {
  font-size: 12px;
  line-height: 1.5;
  color: #6b7280;
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

.mobile-address-row-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--app-text-primary);
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

.mobile-address-row-item strong,
.resource-company-preview {
  font-size: 13px;
  color: #111827;
}

.mobile-address-row-note {
  margin-top: 8px;
}

.resource-filter-form :deep(.el-input__wrapper),
.resource-filter-form :deep(.el-select__wrapper),
.resource-filter-form :deep(.el-date-editor.el-input__wrapper),
.wide-field :deep(.el-select__wrapper),
.wide-field :deep(.el-input__wrapper) {
  min-width: 220px;
}

.address-table :deep(.el-button) {
  padding-inline: 4px;
}

.resource-company-cell {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.resource-company-actions,
.resource-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

@media (max-width: 768px) {
  .mobile-address-row-grid {
    grid-template-columns: 1fr;
  }
}
</style>
