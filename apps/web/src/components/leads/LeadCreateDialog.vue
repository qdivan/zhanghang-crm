<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { apiClient } from "../../api/client";
import FlexibleDateInput from "../shared/FlexibleDateInput.vue";
import type { LeadCreateForm } from "../../views/lead/forms";
import {
  searchLeadCustomers,
  type LeadCustomerSearchItem,
} from "../../views/lead/customerSearch";
import {
  buildLeadDialogSheetHint,
  buildNextReminderDate,
  getDefaultReminderValueForGrade,
  leadGradeOptions,
  leadReminderOptions,
  templateOptions,
} from "../../views/lead/viewMeta";

const props = defineProps<{
  visible: boolean;
  form: LeadCreateForm;
  mode?: "create" | "edit";
  externalMode?: boolean;
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
  submit: [];
}>();

const dialogVisible = computed({
  get: () => props.visible,
  set: (value: boolean) => emit("update:visible", value),
});

const isEditing = computed(() => props.mode === "edit");
const isExternalMode = computed(() => Boolean(props.externalMode));
const isConversionLikeTemplate = computed(() => props.form.template_type !== "FOLLOWUP");
const leadDialogSheetHint = computed(() => buildLeadDialogSheetHint(props.form.template_type));

type CompanySuggestionItem = LeadCustomerSearchItem & {
  value: string;
};

type IntroSuggestionItem = {
  value: string;
};

type SourceSuggestionItem = {
  value: string;
};

const selectedCustomer = ref<LeadCustomerSearchItem | null>(null);

async function fetchCompanySuggestions(
  queryString: string,
  callback: (items: CompanySuggestionItem[]) => void,
) {
  const q = queryString.trim();
  if (!q) {
    callback([]);
    return;
  }

  try {
    const items = await searchLeadCustomers(q);
    callback(items.map((item) => ({ ...item, value: item.name })));
  } catch {
    callback([]);
  }
}

function handleCompanySelect(item: CompanySuggestionItem) {
  selectedCustomer.value = item;
  props.form.related_customer_id = item.id;
  props.form.name = item.name;
  if (!props.form.contact_name) {
    props.form.contact_name = item.contact_name;
  }
  if (!props.form.phone) {
    props.form.phone = item.phone;
  }
}

async function fetchIntroSuggestions(
  queryString: string,
  callback: (items: IntroSuggestionItem[]) => void,
) {
  const q = queryString.trim();
  try {
    const resp = await apiClient.get<string[]>("/leads/intro-options", {
      params: {
        q: q || undefined,
        limit: 12,
      },
    });
    callback(resp.data.map((item) => ({ value: item })));
  } catch {
    callback([]);
  }
}

async function fetchSourceSuggestions(
  queryString: string,
  callback: (items: SourceSuggestionItem[]) => void,
) {
  const q = queryString.trim();
  try {
    const resp = await apiClient.get<string[]>("/leads/source-options", {
      params: {
        q: q || undefined,
        limit: 12,
      },
    });
    callback(resp.data.map((item) => ({ value: item })));
  } catch {
    callback([]);
  }
}

watch(
  () => props.form.name,
  (value) => {
    const trimmed = value.trim();
    if (!trimmed) {
      selectedCustomer.value = null;
      props.form.related_customer_id = null;
      return;
    }
    if (selectedCustomer.value && trimmed !== selectedCustomer.value.name) {
      selectedCustomer.value = null;
      props.form.related_customer_id = null;
    }
  },
);

watch(
  () => props.visible,
  (visible) => {
    if (!visible) {
      selectedCustomer.value = null;
    }
  },
);

watch(
  () => props.form.grade,
  (grade) => {
    const reminderValue = getDefaultReminderValueForGrade(grade);
    if (reminderValue) {
      props.form.reminder_value = reminderValue;
    }
  },
);

watch(
  [() => props.form.contact_start_date, () => props.form.reminder_value],
  ([contactStartDate, reminderValue]) => {
    props.form.next_reminder_at = buildNextReminderDate(contactStartDate, reminderValue);
  },
  { immediate: true },
);
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="isEditing ? '编辑线索' : isExternalMode ? '新增线索' : '新增线索（按 Excel 原型录入）'"
    width="860px"
  >
    <el-form label-position="top">
      <el-alert
        v-if="isExternalMode"
        title="你只能查看和维护自己录入的线索；公司名保存时会自动加上你的项目前缀。"
        type="info"
        :closable="false"
        class="lead-dialog-alert"
      />
      <el-row :gutter="12">
        <el-col v-if="!isExternalMode" :span="6">
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
        <el-col :span="isExternalMode ? 12 : 8">
          <el-form-item label="公司名">
            <el-autocomplete
              v-if="!isExternalMode"
              v-model="props.form.name"
              :fetch-suggestions="fetchCompanySuggestions"
              :trigger-on-focus="false"
              :debounce="200"
              clearable
              placeholder="输入公司名称，可关联已有客户"
              @select="handleCompanySelect"
            >
              <template #default="{ item }">
                <div class="company-suggestion">
                  <span class="company-suggestion__name">{{ item.name }}</span>
                  <el-text size="small" type="info">
                    {{ item.contact_name || "无联系人" }} / {{ item.phone || "无电话" }}
                  </el-text>
                </div>
              </template>
            </el-autocomplete>
            <el-input
              v-else
              v-model="props.form.name"
              clearable
              placeholder="如 青岛示例有限公司"
            />
            <el-text v-if="!props.form.name?.trim()" size="small" type="info">
              留空时会默认使用联系人姓名作为公司名。
            </el-text>
            <el-text v-if="!isExternalMode && props.form.related_customer_id" size="small" type="primary">
              已关联现有客户，后续转化时可选择复用原客户或新建客户主体。
            </el-text>
          </el-form-item>
        </el-col>
        <el-col :span="isExternalMode ? 6 : 5">
          <el-form-item label="等级">
            <el-select v-model="props.form.grade">
              <el-option
                v-for="item in leadGradeOptions"
                :key="`lead-grade-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="isExternalMode ? 6 : 5">
          <el-form-item label="提醒值">
            <el-select v-model="props.form.reminder_value">
              <el-option
                v-for="item in leadReminderOptions"
                :key="`lead-reminder-${item.value}`"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <el-alert v-if="!isExternalMode" type="info" :closable="false" :title="leadDialogSheetHint" class="lead-dialog-alert" />

      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="联系人" required>
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
            <el-form-item label="联络开始时间" required>
              <FlexibleDateInput v-model="props.form.contact_start_date" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="下次提醒">
              <FlexibleDateInput v-model="props.form.next_reminder_at" clearable />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="12">
          <el-col :span="16">
            <el-form-item label="其他联系方式">
              <el-input v-model="props.form.other_contact" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="来源" required>
              <el-autocomplete
                v-model="props.form.source"
                :fetch-suggestions="fetchSourceSuggestions"
                :trigger-on-focus="true"
                :debounce="150"
                clearable
                placeholder="默认 Sally直播，可联想历史来源"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="主营/需要" required>
          <el-input v-model="props.form.main_business" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="介绍人">
          <el-autocomplete
            v-model="props.form.intro"
            :fetch-suggestions="fetchIntroSuggestions"
            :trigger-on-focus="true"
            :debounce="150"
            clearable
            placeholder="可留空，也可复用之前录过的介绍人"
          />
        </el-form-item>

        <el-row v-if="!isExternalMode" :gutter="12">
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
            <el-form-item label="下次提醒">
              <FlexibleDateInput v-model="props.form.next_reminder_at" clearable />
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
            <el-form-item label="来源" required>
              <el-autocomplete
                v-model="props.form.source"
                :fetch-suggestions="fetchSourceSuggestions"
                :trigger-on-focus="true"
                :debounce="150"
                clearable
                placeholder="默认 Sally直播，可联想历史来源"
              />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="提醒值">
              <el-select v-model="props.form.reminder_value">
                <el-option
                  v-for="item in leadReminderOptions"
                  :key="`lead-followup-reminder-${item.value}`"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="其他联系人">
              <el-input v-model="props.form.other_contact" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="主营/需要" required>
          <el-input v-model="props.form.main_business" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="介绍人">
          <el-autocomplete
            v-model="props.form.intro"
            :fetch-suggestions="fetchIntroSuggestions"
            :trigger-on-focus="true"
            :debounce="150"
            clearable
            placeholder="可留空，也可复用之前录过的介绍人"
          />
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

.company-suggestion {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.company-suggestion__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
