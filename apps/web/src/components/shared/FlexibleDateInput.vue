<script setup lang="ts">
import { Calendar } from "@element-plus/icons-vue";
import { computed, ref, watch } from "vue";

import { normalizeDateText } from "../../utils/dateInput";

const props = withDefaults(
  defineProps<{
    modelValue: string | null;
    placeholder?: string;
    disabled?: boolean;
    clearable?: boolean;
    emptyValue?: string | null;
  }>(),
  {
    placeholder: "YYYYMMDD 或 YYMMDD",
    disabled: false,
    clearable: false,
    emptyValue: null,
  },
);

const emit = defineEmits<{
  "update:modelValue": [value: string | null];
}>();

const textValue = ref(props.modelValue ?? "");
const nativeDateInput = ref<HTMLInputElement | null>(null);

watch(
  () => props.modelValue,
  (value) => {
    const nextValue = value ?? "";
    if (nextValue !== textValue.value) {
      textValue.value = nextValue;
    }
  },
);

const nativePickerValue = computed(() => normalizeDateText(textValue.value) ?? "");

function updateValue(value: string | null) {
  textValue.value = value ?? "";
  emit("update:modelValue", value);
}

function commitText() {
  const rawText = textValue.value.trim();
  if (!rawText) {
    updateValue(props.emptyValue);
    return;
  }
  updateValue(normalizeDateText(rawText) ?? rawText);
}

function clearValue() {
  updateValue(props.emptyValue);
}

function openNativePicker() {
  if (props.disabled) {
    return;
  }
  const input = nativeDateInput.value;
  if (!input) {
    return;
  }
  if (typeof (input as HTMLInputElement & { showPicker?: () => void }).showPicker === "function") {
    (input as HTMLInputElement & { showPicker?: () => void }).showPicker?.();
    return;
  }
  input.click();
}

function handleNativeChange(event: Event) {
  const input = event.target;
  if (!(input instanceof HTMLInputElement)) {
    return;
  }
  updateValue(input.value || props.emptyValue);
}
</script>

<template>
  <div class="flex-date-input">
    <el-input
      v-model="textValue"
      :placeholder="props.placeholder"
      :disabled="props.disabled"
      :clearable="props.clearable"
      @keydown.enter.prevent="commitText"
      @blur="commitText"
      @clear="clearValue"
    >
      <template #suffix>
        <el-button
          link
          class="calendar-trigger"
          :disabled="props.disabled"
          @click.prevent="openNativePicker"
        >
          <el-icon><Calendar /></el-icon>
        </el-button>
      </template>
    </el-input>
    <input
      ref="nativeDateInput"
      class="native-date-proxy"
      type="date"
      :value="nativePickerValue"
      tabindex="-1"
      aria-hidden="true"
      @change="handleNativeChange"
    />
  </div>
</template>

<style scoped>
.flex-date-input {
  position: relative;
  width: 100%;
}

.calendar-trigger {
  padding: 0;
  min-height: auto;
}

.native-date-proxy {
  position: absolute;
  inset: auto 0 0 auto;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}
</style>
