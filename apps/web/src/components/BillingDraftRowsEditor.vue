<script setup lang="ts">
import { CopyDocument, Delete, Plus, QuestionFilled } from "@element-plus/icons-vue";
import { computed, ref } from "vue";

import FlexibleDateInput from "./shared/FlexibleDateInput.vue";
import type { BillingCreatePayload } from "../types";
import {
  billingCycleOptions,
  billingFieldHelp,
  billingStatusOptions,
  chargeCategoryOptions,
  chargeModeOptions,
  cloneBillingDraft,
  createEmptyBillingDraft,
  getAmountBasisOptions,
  getMonthlyFeeLabel,
  paymentMethodOptions,
  syncBillingDerivedDates,
} from "../utils/billingDraft";

const props = withDefaults(
  defineProps<{
    modelValue: BillingCreatePayload[];
    titlePrefix?: string;
    allowMultiple?: boolean;
  }>(),
  {
    allowMultiple: true,
  },
);

const emit = defineEmits<{
  (e: "update:modelValue", value: BillingCreatePayload[]): void;
}>();

const titlePrefix = computed(() => props.titlePrefix || "收费项");
const allowMultiple = computed(() => props.allowMultiple);
const expandedAdvancedPanels = ref<string[]>([]);

function updateRows(nextRows: BillingCreatePayload[]) {
  emit("update:modelValue", nextRows);
}

function normalizeDraft(draft: BillingCreatePayload, options: { recalculateDue?: boolean } = {}) {
  const nextDraft = cloneBillingDraft(draft);
  syncBillingDerivedDates(nextDraft, options);
  return nextDraft;
}

function patchRow(index: number, patch: Partial<BillingCreatePayload>, options: { recalculateDue?: boolean } = {}) {
  const nextRows = props.modelValue.map((item, itemIndex) => {
    const nextItem = itemIndex === index ? { ...cloneBillingDraft(item), ...patch } : cloneBillingDraft(item);
    return normalizeDraft(nextItem, itemIndex === index ? options : {});
  });
  updateRows(nextRows);
}

function setStringField<K extends keyof BillingCreatePayload>(index: number, key: K, value: unknown) {
  patchRow(index, { [key]: String(value ?? "") } as Pick<BillingCreatePayload, K>);
}

function setNumberField<K extends keyof BillingCreatePayload>(index: number, key: K, value: unknown) {
  patchRow(index, { [key]: Number(value ?? 0) } as Pick<BillingCreatePayload, K>);
}

function setNullableNumberField<K extends keyof BillingCreatePayload>(index: number, key: K, value: unknown) {
  const normalized = value === null || value === undefined || value === "" ? null : Number(value);
  patchRow(index, { [key]: normalized } as Pick<BillingCreatePayload, K>);
}

function setChargeMode(index: number, value: BillingCreatePayload["charge_mode"]) {
  patchRow(index, { charge_mode: value }, { recalculateDue: true });
}

function setAmountBasis(index: number, value: BillingCreatePayload["amount_basis"]) {
  patchRow(index, { amount_basis: value }, { recalculateDue: true });
}

function setCollectionStartDate(index: number, value: string) {
  patchRow(index, { collection_start_date: value }, { recalculateDue: true });
}

function setDueDate(index: number, value: string) {
  patchRow(index, { due_month: value });
}

function addRow() {
  if (!allowMultiple.value) return;
  const customerId = props.modelValue[0]?.customer_id ?? null;
  updateRows([...props.modelValue.map(cloneBillingDraft), createEmptyBillingDraft(customerId)]);
}

function duplicateRow(index: number) {
  if (!allowMultiple.value) return;
  const nextRows = props.modelValue.map(cloneBillingDraft);
  nextRows.splice(index + 1, 0, {
    ...cloneBillingDraft(props.modelValue[index]),
    serial_no: null,
    received_amount: 0,
    status: "PARTIAL",
  });
  updateRows(nextRows.map((item) => normalizeDraft(item)));
}

function removeRow(index: number) {
  if (props.modelValue.length <= 1) return;
  updateRows(props.modelValue.filter((_, itemIndex) => itemIndex !== index).map(cloneBillingDraft));
}

function advancedPanelName(index: number) {
  return `advanced-${index}`;
}
</script>

<template>
  <div class="billing-draft-editor">
    <el-card
      v-for="(item, index) in modelValue"
      :key="`billing-draft-${index}`"
      shadow="never"
      class="billing-draft-card"
    >
      <template #header>
        <div class="billing-draft-card__header">
          <div class="billing-draft-card__title">
            <span>{{ titlePrefix }} {{ index + 1 }}</span>
            <el-tag size="small" effect="plain">{{ item.charge_category }}</el-tag>
            <el-tag size="small" effect="plain" type="success">
              {{ item.charge_mode === "ONE_TIME" ? "按次" : "按期" }}
            </el-tag>
          </div>
          <el-space>
            <el-button v-if="allowMultiple" :icon="CopyDocument" link type="primary" @click="duplicateRow(index)">
              复制一行
            </el-button>
            <el-button
              v-if="allowMultiple"
              :icon="Delete"
              link
              type="danger"
              :disabled="modelValue.length <= 1"
              @click="removeRow(index)"
            >
              删除本行
            </el-button>
          </el-space>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        class="billing-draft-card__tip"
        :title="
          item.charge_mode === 'ONE_TIME'
            ? '按次项目默认服务开始日期=到期日期；金额口径固定为单次费用。'
            : '按期项目只需要录服务开始日期和到期日期，内部开始/结束月份由系统自动推导。'
        "
      />

      <el-form label-position="top">
        <el-row :gutter="12">
          <el-col :xs="24" :md="6">
            <el-form-item>
              <template #label>
                <span class="label-with-help">
                  收费类别
                  <el-tooltip placement="top" :show-after="150" :content="billingFieldHelp.charge_category">
                    <el-icon class="help-icon"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </span>
              </template>
              <el-select
                :model-value="item.charge_category"
                @update:model-value="setStringField(index, 'charge_category', $event)"
              >
                <el-option
                  v-for="category in chargeCategoryOptions"
                  :key="`billing-category-${index}-${category}`"
                  :label="category"
                  :value="category"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="6">
            <el-form-item>
              <template #label>
                <span class="label-with-help">
                  计费方式
                  <el-tooltip placement="top" :show-after="150" :content="billingFieldHelp.charge_mode">
                    <el-icon class="help-icon"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </span>
              </template>
              <el-select :model-value="item.charge_mode" @update:model-value="setChargeMode(index, $event)">
                <el-option
                  v-for="mode in chargeModeOptions"
                  :key="`billing-mode-${index}-${mode.value}`"
                  :label="mode.label"
                  :value="mode.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="6">
            <el-form-item>
              <template #label>
                <span class="label-with-help">
                  金额口径
                  <el-tooltip placement="top" :show-after="150" :content="billingFieldHelp.amount_basis">
                    <el-icon class="help-icon"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </span>
              </template>
              <el-select :model-value="item.amount_basis" @update:model-value="setAmountBasis(index, $event)">
                <el-option
                  v-for="basis in getAmountBasisOptions(item.charge_mode)"
                  :key="`billing-basis-${index}-${basis.value}`"
                  :label="basis.label"
                  :value="basis.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="6">
            <el-form-item>
              <template #label>
                <span class="label-with-help">
                  付款方式
                  <el-tooltip placement="top" :show-after="150" :content="billingFieldHelp.payment_method">
                    <el-icon class="help-icon"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </span>
              </template>
              <el-select
                :model-value="item.payment_method"
                @update:model-value="setStringField(index, 'payment_method', $event)"
              >
                <el-option
                  v-for="payment in paymentMethodOptions"
                  :key="`billing-payment-${index}-${payment.value}`"
                  :label="payment.label"
                  :value="payment.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="12">
          <el-col :xs="24" :md="12">
            <el-form-item>
              <template #label>
                <span class="label-with-help">
                  摘要
                  <el-tooltip placement="top" :show-after="150" :content="billingFieldHelp.summary">
                    <el-icon class="help-icon"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </span>
              </template>
              <el-input
                :model-value="item.summary"
                placeholder="例如：2026年度代账服务"
                @update:model-value="setStringField(index, 'summary', $event)"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="6">
            <el-form-item>
              <template #label>
                <span class="label-with-help">
                  总费用
                  <el-tooltip placement="top" :show-after="150" :content="billingFieldHelp.total_fee">
                    <el-icon class="help-icon"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </span>
              </template>
              <el-input-number
                :model-value="item.total_fee"
                :min="0"
                :controls="false"
                style="width: 100%"
                @update:model-value="setNumberField(index, 'total_fee', $event)"
              />
            </el-form-item>
          </el-col>
          <el-col v-if="item.charge_mode === 'PERIODIC'" :xs="24" :md="6">
            <el-form-item>
              <template #label>
                <span class="label-with-help">
                  {{ getMonthlyFeeLabel(item) }}
                  <el-tooltip placement="top" :show-after="150" :content="billingFieldHelp.monthly_fee">
                    <el-icon class="help-icon"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </span>
              </template>
              <el-input-number
                :model-value="item.monthly_fee"
                :min="0"
                :controls="false"
                style="width: 100%"
                @update:model-value="setNumberField(index, 'monthly_fee', $event)"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="12">
          <el-col :xs="24" :md="12">
            <el-form-item>
              <template #label>
                <span class="label-with-help">
                  服务开始日期
                  <el-tooltip placement="top" :show-after="150" :content="billingFieldHelp.collection_start_date">
                    <el-icon class="help-icon"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </span>
              </template>
              <FlexibleDateInput
                :model-value="item.collection_start_date"
                :empty-value="''"
                @update:model-value="setCollectionStartDate(index, String($event ?? ''))"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item>
              <template #label>
                <span class="label-with-help">
                  到期日期
                  <el-tooltip placement="top" :show-after="150" :content="billingFieldHelp.due_month">
                    <el-icon class="help-icon"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </span>
              </template>
              <FlexibleDateInput
                :model-value="item.due_month"
                :empty-value="''"
                @update:model-value="setDueDate(index, String($event ?? ''))"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <div class="billing-draft-hint">
          <el-text type="info" size="small">
            {{
              item.charge_mode === "ONE_TIME"
                ? "按次项目默认用服务开始日期作为到期日期；若实际完成日不同，可手动改。"
                : "按期项目会按服务开始日期 + 金额口径先给出默认到期日期；内部开始/结束月份自动推导，无需重复填写。"
            }}
          </el-text>
        </div>

        <el-form-item>
          <template #label>
            <span class="label-with-help">
              备注
              <el-tooltip placement="top" :show-after="150" :content="billingFieldHelp.note">
                <el-icon class="help-icon"><QuestionFilled /></el-icon>
              </el-tooltip>
            </span>
          </template>
          <el-input
            :model-value="item.note"
            type="textarea"
            :rows="2"
            placeholder="例如：含退税服务 / 需老板复核 / 约定分两次收款"
            @update:model-value="setStringField(index, 'note', $event)"
          />
        </el-form-item>

        <el-collapse v-model="expandedAdvancedPanels" class="billing-draft-advanced">
          <el-collapse-item :name="advancedPanelName(index)">
            <template #title>
              <span class="label-with-help">
                高级项（到账/说明/历史补录）
                <el-tooltip placement="top" :show-after="150" content="常规新单通常不需要展开；历史单据补录或已收部分款项时再填写。">
                  <el-icon class="help-icon"><QuestionFilled /></el-icon>
                </el-tooltip>
              </span>
            </template>

            <el-row :gutter="12">
              <el-col :xs="24" :md="6">
                <el-form-item>
                  <template #label>
                    <span class="label-with-help">
                      序号
                      <el-tooltip placement="top" :show-after="150" :content="billingFieldHelp.serial_no">
                        <el-icon class="help-icon"><QuestionFilled /></el-icon>
                      </el-tooltip>
                    </span>
                  </template>
                  <el-input-number
                    :model-value="item.serial_no"
                    :min="1"
                    :controls="false"
                    style="width: 100%"
                    placeholder="留空自动编号"
                    @update:model-value="setNullableNumberField(index, 'serial_no', $event)"
                  />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="6">
                <el-form-item>
                  <template #label>
                    <span class="label-with-help">
                      台账状态
                      <el-tooltip placement="top" :show-after="150" :content="billingFieldHelp.status">
                        <el-icon class="help-icon"><QuestionFilled /></el-icon>
                      </el-tooltip>
                    </span>
                  </template>
                  <el-select :model-value="item.status" @update:model-value="setStringField(index, 'status', $event)">
                    <el-option
                      v-for="statusItem in billingStatusOptions"
                      :key="`billing-status-${index}-${statusItem.value}`"
                      :label="statusItem.label"
                      :value="statusItem.value"
                    />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="6">
                <el-form-item>
                  <template #label>
                    <span class="label-with-help">
                      已收金额
                      <el-tooltip placement="top" :show-after="150" :content="billingFieldHelp.received_amount">
                        <el-icon class="help-icon"><QuestionFilled /></el-icon>
                      </el-tooltip>
                    </span>
                  </template>
                  <el-input-number
                    :model-value="item.received_amount"
                    :min="0"
                    :controls="false"
                    style="width: 100%"
                    @update:model-value="setNumberField(index, 'received_amount', $event)"
                  />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="6">
                <el-form-item>
                  <template #label>
                    <span class="label-with-help">
                      周期说明
                      <el-tooltip placement="top" :show-after="150" :content="billingFieldHelp.billing_cycle_text">
                        <el-icon class="help-icon"><QuestionFilled /></el-icon>
                      </el-tooltip>
                    </span>
                  </template>
                  <el-select
                    :model-value="item.billing_cycle_text"
                    placeholder="请选择周期说明"
                    @update:model-value="setStringField(index, 'billing_cycle_text', $event)"
                  >
                    <el-option
                      v-for="cycle in billingCycleOptions"
                      :key="`billing-cycle-${index}-${cycle}`"
                      :label="cycle"
                      :value="cycle"
                    />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item>
              <template #label>
                <span class="label-with-help">
                  扩展说明
                  <el-tooltip placement="top" :show-after="150" :content="billingFieldHelp.extra_note">
                    <el-icon class="help-icon"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </span>
              </template>
              <el-input
                :model-value="item.extra_note"
                placeholder="例如：同步给注册同事 / 客户要求月底前出结果"
                @update:model-value="setStringField(index, 'extra_note', $event)"
              />
            </el-form-item>
          </el-collapse-item>
        </el-collapse>
      </el-form>
    </el-card>

    <div v-if="allowMultiple" class="billing-draft-editor__actions">
      <el-button :icon="Plus" type="primary" plain @click="addRow">新增收费项</el-button>
    </div>
  </div>
</template>

<style scoped>
.billing-draft-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.billing-draft-card {
  border-radius: 12px;
}

.billing-draft-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.billing-draft-card__title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-weight: 600;
}

.billing-draft-card__tip {
  margin-bottom: 12px;
}

.billing-draft-editor__actions {
  display: flex;
  justify-content: center;
}

.billing-draft-hint {
  margin-bottom: 12px;
}

.billing-draft-advanced {
  margin-top: 8px;
}

.label-with-help {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.help-icon {
  color: var(--el-text-color-secondary);
  cursor: help;
}

@media (max-width: 768px) {
  .billing-draft-card__header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
