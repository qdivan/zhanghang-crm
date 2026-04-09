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
  userOptions: UserLite[];
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
  <el-dialog v-model="dialogVisible" title="转化并分配负责人员" width="760px" class="lead-convert-dialog">
    <el-form label-position="top" class="convert-form">
      <div class="convert-shell">
        <section class="convert-section convert-section-intro">
          <div class="convert-section-head">
            <div>
              <div class="convert-section-title">转化方式</div>
              <div class="convert-section-copy">先确认这次是新建客户主体，还是直接复用老客户继续成交。</div>
            </div>
          </div>
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
        </section>

        <section class="convert-section">
          <div class="convert-section-head">
            <div>
              <div class="convert-section-title">客户创建信息</div>
              <div class="convert-section-copy">把这次成交要落在哪个客户主体下先写清楚，后续收费和事项都会跟着这里走。</div>
            </div>
          </div>
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
        </section>

        <div class="convert-section-grid">
          <section class="convert-section">
            <div class="convert-section-head">
              <div>
                <div class="convert-section-title">客户编号</div>
                <div class="convert-section-copy">数字部分按连续编号走，后缀会先按来源或介绍人带出，你也可以手动改。</div>
              </div>
              <div class="convert-code-preview">{{ customerCodePreview }}</div>
            </div>
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
          </section>

          <section class="convert-section">
            <div class="convert-section-head">
              <div>
                <div class="convert-section-title">负责人</div>
                <div class="convert-section-copy">先确定当前主负责人；如果这次还没到会计承接，也可以暂时不选会计负责人。</div>
              </div>
            </div>
            <el-form-item label="负责人员">
              <el-select v-model="props.form.responsible_user_id" placeholder="请选择负责人员" filterable>
                <el-option
                  v-for="item in props.userOptions"
                  :key="item.id"
                  :label="`${item.username}（${item.role}）`"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="会计负责人（可选）">
              <el-select v-model="props.form.assigned_accountant_id" placeholder="后续再指定也可以" clearable filterable>
                <el-option
                  v-for="item in props.accountantOptions"
                  :key="`accountant-${item.id}`"
                  :label="item.username"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
          </section>
        </div>
      </div>
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

<style scoped>
.convert-form :deep(.el-select),
.convert-form :deep(.el-input-number),
.convert-form :deep(.el-radio-group) {
  width: 100%;
}

.convert-shell {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.convert-section {
  padding: 16px 18px 4px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.94));
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
}

.convert-section-intro {
  padding-bottom: 16px;
}

.convert-section-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.convert-section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.convert-section-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.convert-section-copy {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--app-text-muted);
}

.convert-code-preview {
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(77, 128, 150, 0.12);
  color: var(--app-accent-strong);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .convert-section-grid {
    grid-template-columns: 1fr;
  }

  .convert-section-head {
    flex-direction: column;
  }

  .convert-code-preview {
    align-self: flex-start;
  }
}
</style>
