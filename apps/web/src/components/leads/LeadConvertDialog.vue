<script setup lang="ts">
import { computed } from "vue";

import type { LeadConvertForm } from "../../views/lead/forms";

type UserLite = {
  id: number;
  username: string;
  role: string;
};

const props = defineProps<{
  visible: boolean;
  targetLeadName: string;
  form: LeadConvertForm;
  accountantOptions: UserLite[];
  loading: boolean;
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
  submit: [];
  "submit-and-add-billing": [];
}>();

const dialogVisible = computed({
  get: () => props.visible,
  set: (value: boolean) => emit("update:visible", value),
});
</script>

<template>
  <el-dialog v-model="dialogVisible" title="转化并分配会计" width="560px">
    <el-form label-position="top">
      <el-form-item label="线索">
        <el-input :model-value="props.targetLeadName" disabled />
      </el-form-item>
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="转化后客户名称">
            <el-input v-model="props.form.customer_name" placeholder="可与线索名称不同" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="转化后联系人">
            <el-input v-model="props.form.customer_contact_name" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="转化后电话">
        <el-input v-model="props.form.customer_phone" />
      </el-form-item>
      <el-form-item label="分配会计">
        <el-select v-model="props.form.accountant_id" placeholder="请选择会计">
          <el-option
            v-for="item in props.accountantOptions"
            :key="item.id"
            :label="item.username"
            :value="item.id"
          />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" plain :loading="props.loading" @click="emit('submit')">确认转化</el-button>
      <el-button type="primary" :loading="props.loading" @click="emit('submit-and-add-billing')">
        确认转化并添加收费信息
      </el-button>
    </template>
  </el-dialog>
</template>
