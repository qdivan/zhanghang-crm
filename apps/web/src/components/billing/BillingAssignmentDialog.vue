<script setup lang="ts">
import { computed } from "vue";

import type { BillingAssignmentItem, BillingRecord } from "../../types";
import type { BillingAssignmentForm } from "../../views/billing/forms";
import {
  assignmentKindLabel,
  assignmentKindOptions,
  assignmentRoleLabel,
  assignmentRoleOptions,
} from "../../views/billing/viewMeta";

type UserLite = {
  id: number;
  username: string;
  role: string;
};

const props = defineProps<{
  visible: boolean;
  targetRecord: BillingRecord | null;
  form: BillingAssignmentForm;
  users: UserLite[];
  loading: boolean;
  submitting: boolean;
  rows: BillingAssignmentItem[];
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
  submit: [];
  deactivate: [row: BillingAssignmentItem];
}>();

const dialogVisible = computed({
  get: () => props.visible,
  set: (value: boolean) => emit("update:visible", value),
});

const dialogTitle = computed(() => `派工 / 推送 - ${props.targetRecord?.customer_name ?? ""}`);
</script>

<template>
  <el-dialog v-model="dialogVisible" :title="dialogTitle" width="760px">
    <el-form label-position="top">
      <el-row :gutter="12">
        <el-col :span="10">
          <el-form-item label="派给谁">
            <el-select v-model="props.form.assignee_user_id" filterable placeholder="请选择执行人员">
              <el-option
                v-for="item in props.users"
                :key="`assign-user-${item.id}`"
                :label="`${item.username}（${item.role}）`"
                :value="item.id"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="分派方式">
            <el-select v-model="props.form.assignment_kind">
              <el-option
                v-for="item in assignmentKindOptions"
                :key="`assignment-kind-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="业务角色">
            <el-select v-model="props.form.assignment_role">
              <el-option
                v-for="item in assignmentRoleOptions"
                :key="`assignment-role-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="4">
          <el-form-item label="操作">
            <el-button type="primary" :loading="props.submitting" @click="emit('submit')">确认派工</el-button>
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="说明">
        <el-input v-model="props.form.note" placeholder="可选：填写分派说明，例如负责股权变更办理" />
      </el-form-item>
    </el-form>

    <el-divider />

    <el-table v-loading="props.loading" :data="props.rows" stripe border>
      <el-table-column prop="assignee_username" label="执行人员" width="130" />
      <el-table-column prop="assignee_role" label="系统角色" width="110" />
      <el-table-column label="分派方式" width="110">
        <template #default="{ row }">
          {{ assignmentKindLabel(row.assignment_kind) }}
        </template>
      </el-table-column>
      <el-table-column label="业务角色" width="120">
        <template #default="{ row }">
          {{ assignmentRoleLabel(row.assignment_role) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? "生效" : "停用" }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="note" label="说明" min-width="160" show-overflow-tooltip />
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button link type="danger" :disabled="!row.is_active" @click="emit('deactivate', row)">
            结束
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-dialog>
</template>
