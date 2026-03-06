<script setup lang="ts">
import { computed } from "vue";

import FlexibleDateInput from "../shared/FlexibleDateInput.vue";
import type { LeadRedevelopForm } from "../../views/lead/forms";

type CustomerSearchItem = {
  id: number;
  name: string;
  contact_name: string;
  phone: string;
  assigned_accountant_id: number;
  accountant_username: string;
};

const props = defineProps<{
  visible: boolean;
  form: LeadRedevelopForm;
  options: CustomerSearchItem[];
  searchLoading: boolean;
  submitting: boolean;
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
  search: [keyword: string];
  submit: [];
}>();

const dialogVisible = computed({
  get: () => props.visible,
  set: (value: boolean) => emit("update:visible", value),
});

function remoteSearch(keyword: string) {
  emit("search", keyword);
}
</script>

<template>
  <el-dialog v-model="dialogVisible" title="老客二次开发" width="680px">
    <el-form label-position="top">
      <el-form-item label="搜索客户（客户名 / 老板 / 联系人）">
        <el-select
          v-model="props.form.customer_id"
          filterable
          remote
          reserve-keyword
          clearable
          placeholder="输入客户名称或联系人后搜索"
          :remote-method="remoteSearch"
          :loading="props.searchLoading"
          style="width: 100%"
        >
          <el-option
            v-for="item in props.options"
            :key="`redevelop-customer-${item.id}`"
            :label="`${item.name}（${item.contact_name}）`"
            :value="item.id"
          >
            <div class="redevelop-option">
              <span>{{ item.name }}（{{ item.contact_name }}）</span>
              <el-text type="info" size="small">{{ item.accountant_username }}</el-text>
            </div>
          </el-option>
        </el-select>
      </el-form-item>
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="线索来源">
            <el-input v-model="props.form.source" placeholder="默认：老客户二次开发" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="下次提醒">
            <FlexibleDateInput v-model="props.form.next_reminder_at" clearable />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="本次开发需求">
        <el-input
          v-model="props.form.notes"
          type="textarea"
          :rows="3"
          placeholder="例如：新增股权变更服务，预计本周转成交并录入费用"
        />
      </el-form-item>
      <el-text type="info" size="small">
        创建后会生成一条“老客二开线索”，成交时复用原客户，不会重复建客户档案。
      </el-text>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="props.submitting" @click="emit('submit')">创建二开线索</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.redevelop-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
</style>
