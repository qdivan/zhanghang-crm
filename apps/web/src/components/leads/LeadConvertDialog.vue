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

const customerCodePreview = computed(() => {
  const seq = props.form.customer_code_seq ? String(props.form.customer_code_seq).padStart(4, "0") : "自动";
  const suffix = (props.form.customer_code_suffix || "").trim().toUpperCase() || "A";
  return `${seq}${suffix}`;
});
</script>

<template>
  <el-dialog v-model="dialogVisible" title="转化并分配会计" width="640px">
    <el-form label-position="top">
      <el-form-item label="线索">
        <el-input :model-value="props.targetLeadName" disabled />
      </el-form-item>
      <el-form-item label="转化方式">
        <el-radio-group v-model="props.form.conversion_mode">
          <el-radio-button value="NEW_CUSTOMER_LINKED">新建客户主体并关联原客户</el-radio-button>
          <el-radio-button value="REUSE_CUSTOMER">复用原客户</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-alert
        v-if="props.form.conversion_mode === 'REUSE_CUSTOMER'"
        type="warning"
        :closable="false"
        title="复用原客户时，不会新建客户档案；本次成交仍会新增收费和后续办理记录。"
      />
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="转化后客户名称">
            <el-input v-model="props.form.customer_name" placeholder="可与线索名称不同，老客二开可填新公司名" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="转化后联系人">
            <el-input v-model="props.form.customer_contact_name" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="转化后电话">
        <el-input v-model="props.form.customer_phone" placeholder="可选填" />
      </el-form-item>
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="客户编号">
            <el-input-number
              v-model="props.form.customer_code_seq"
              :min="1"
              :controls="false"
              style="width: 100%"
              placeholder="留空则自动连续编号"
            />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="编号后缀">
            <el-input v-model="props.form.customer_code_suffix" maxlength="8" placeholder="默认按来源/介绍人带出" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="完整编号预览">
        <el-input :model-value="customerCodePreview" disabled />
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
