<script setup lang="ts">
import { computed } from "vue";

import FlexibleDateInput from "../shared/FlexibleDateInput.vue";
import type { LeadCreateForm } from "../../views/lead/forms";
import { buildLeadDialogSheetHint, templateOptions } from "../../views/lead/viewMeta";

const props = defineProps<{
  visible: boolean;
  form: LeadCreateForm;
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
  submit: [];
}>();

const dialogVisible = computed({
  get: () => props.visible,
  set: (value: boolean) => emit("update:visible", value),
});

const isConversionLikeTemplate = computed(() => props.form.template_type !== "FOLLOWUP");
const leadDialogSheetHint = computed(() => buildLeadDialogSheetHint(props.form.template_type));
</script>

<template>
  <el-dialog v-model="dialogVisible" title="新增线索（按 Excel 原型录入）" width="860px">
    <el-form label-position="top">
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="来源模板">
            <el-select v-model="props.form.template_type">
              <el-option
                v-for="item in templateOptions"
                :key="`lead-template-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="公司名">
            <el-input v-model="props.form.name" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="等级">
            <el-input v-model="props.form.grade" placeholder="A/B/C..." />
          </el-form-item>
        </el-col>
      </el-row>

      <el-alert type="info" :closable="false" :title="leadDialogSheetHint" class="lead-dialog-alert" />

      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="联系人">
            <el-input v-model="props.form.contact_name" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="电话">
            <el-input v-model="props.form.phone" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="微信号">
            <el-input v-model="props.form.contact_wechat" />
          </el-form-item>
        </el-col>
      </el-row>

      <template v-if="isConversionLikeTemplate">
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="地区">
              <el-input v-model="props.form.region" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="联络开始时间">
              <FlexibleDateInput v-model="props.form.contact_start_date" clearable />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="提醒值">
              <el-input v-model="props.form.reminder_value" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="传真">
              <el-input v-model="props.form.fax" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="其他联系方式">
              <el-input v-model="props.form.other_contact" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="下次提醒">
              <FlexibleDateInput v-model="props.form.next_reminder_at" clearable />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="主营/需求">
          <el-input v-model="props.form.main_business" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="介绍">
          <el-input v-model="props.form.intro" />
        </el-form-item>

        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="备用2">
              <el-input v-model="props.form.reserve_2" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="备用3">
              <el-input v-model="props.form.reserve_3" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="备用4">
              <el-input v-model="props.form.reserve_4" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="备注">
          <el-input v-model="props.form.notes" type="textarea" :rows="2" />
        </el-form-item>
      </template>

      <template v-else>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="国家/业务类型">
              <el-input v-model="props.form.country" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="服务开始时间">
              <el-input v-model="props.form.service_start_text" placeholder="如 2025.07.02" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="提醒值">
              <el-input v-model="props.form.reminder_value" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="企业性质">
              <el-input v-model="props.form.company_nature" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="服务方式">
              <el-input v-model="props.form.service_mode" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="下次提醒">
              <FlexibleDateInput v-model="props.form.next_reminder_at" clearable />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="来源">
              <el-input v-model="props.form.source" />
            </el-form-item>
          </el-col>
          <el-col :span="16">
            <el-form-item label="其他联系人">
              <el-input v-model="props.form.other_contact" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="主营产品">
          <el-input v-model="props.form.main_business" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="介绍">
          <el-input v-model="props.form.intro" />
        </el-form-item>

        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="收费标准">
              <el-input v-model="props.form.fee_standard" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="首期账单期间">
              <el-input v-model="props.form.first_billing_period" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="备注">
          <el-input v-model="props.form.notes" type="textarea" :rows="2" />
        </el-form-item>
      </template>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="emit('submit')">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.lead-dialog-alert {
  margin-bottom: 12px;
}
</style>
