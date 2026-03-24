<script setup lang="ts">
import { ArrowRight } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { reactive } from "vue";
import { useRouter } from "vue-router";

import { useAuthStore } from "../stores/auth";

const router = useRouter();
const auth = useAuthStore();

const form = reactive({
  username: "",
  password: "",
});

const state = reactive({
  loading: false,
});

const scopeItems = ["客户开发", "客户列表", "收费明细", "到账核对"];

async function login() {
  if (!form.username || !form.password) {
    ElMessage.warning("请输入账号和密码");
    return;
  }
  state.loading = true;
  try {
    await auth.login(form.username, form.password);
    ElMessage.success("登录成功");
    router.push("/leads");
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "账号或密码错误");
  } finally {
    state.loading = false;
  }
}

function openPublicLibrary() {
  router.push("/library/public");
}
</script>

<template>
  <section class="login-page">
    <div class="login-shell">
      <section class="login-intro">
        <div class="login-mark">账航·一帆财税</div>
        <h1 class="login-title">代账团队内部系统</h1>
        <p class="login-copy">开发、客户、收费、核对都在同一套流程里处理。</p>

        <div class="login-scope-grid">
          <div v-for="item in scopeItems" :key="item" class="login-scope-item">
            {{ item }}
          </div>
        </div>

        <div class="login-notes">
          <div class="login-note-row">
            <span class="login-note-label">开发</span>
            <span class="login-note-value">只管成单前线索</span>
          </div>
          <div class="login-note-row">
            <span class="login-note-label">客户</span>
            <span class="login-note-value">成单后交给会计或经办人</span>
          </div>
          <div class="login-note-row">
            <span class="login-note-label">收费</span>
            <span class="login-note-value">收费单、催收、到账、往来账分开看</span>
          </div>
        </div>
      </section>

      <section class="login-panel">
        <div class="login-panel-head">
          <div class="login-panel-title">登录</div>
          <div class="login-panel-copy">本地账号登录，后续可继续接 LDAP。</div>
        </div>

        <el-form :model="form" label-position="top" class="login-form" @submit.prevent="login">
          <el-form-item label="账号">
            <el-input v-model="form.username" placeholder="请输入账号" size="large" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input
              v-model="form.password"
              type="password"
              show-password
              placeholder="请输入密码"
              size="large"
            />
          </el-form-item>
          <el-button class="login-submit" type="primary" :loading="state.loading" @click="login">
            进入系统
          </el-button>
        </el-form>

        <div class="login-panel-foot">
          <button class="login-secondary-link" @click="openPublicLibrary">
            查看公开资料
            <el-icon><ArrowRight /></el-icon>
          </button>
        </div>
      </section>
    </div>
  </section>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  background:
    linear-gradient(180deg, #ffffff 0%, #ffffff 62%, #f6f8f8 100%);
}

.login-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 40px;
  padding: clamp(24px, 4vw, 48px);
}

.login-intro,
.login-panel {
  opacity: 0;
  transform: translateY(12px);
  animation: fade-up 420ms ease forwards;
}

.login-intro {
  display: flex;
  flex-direction: column;
  justify-content: center;
  max-width: 720px;
}

.login-mark {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  padding: 7px 12px;
  border: 1px solid #d8e3e6;
  background: #f5f8f8;
  font-size: 13px;
  font-weight: 600;
  color: #315c73;
}

.login-title {
  margin: 20px 0 10px;
  font-size: clamp(34px, 5vw, 56px);
  line-height: 1.02;
  letter-spacing: -0.04em;
  color: #192531;
}

.login-copy {
  margin: 0;
  max-width: 460px;
  color: #61707c;
  font-size: 16px;
  line-height: 1.75;
}

.login-scope-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 180px));
  gap: 10px;
  margin-top: 28px;
}

.login-scope-item {
  padding: 14px 16px;
  background: #f5f8f8;
  border: 1px solid #dde5e7;
  color: #22303b;
  font-weight: 600;
}

.login-notes {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #e6ecee;
  max-width: 560px;
}

.login-note-row {
  display: grid;
  grid-template-columns: 52px 1fr;
  gap: 12px;
  align-items: baseline;
}

.login-note-label {
  font-size: 12px;
  font-weight: 600;
  color: #5b8471;
  letter-spacing: 0.06em;
}

.login-note-value {
  color: #5f6f7b;
  line-height: 1.7;
}

.login-panel {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 28px;
  border: 1px solid #dde5e7;
  background: #ffffff;
  box-shadow: 0 18px 42px rgba(19, 34, 49, 0.05);
  animation-delay: 80ms;
}

.login-panel-head {
  margin-bottom: 16px;
}

.login-panel-title {
  font-size: 28px;
  font-weight: 700;
  color: #182635;
}

.login-panel-copy {
  margin-top: 6px;
  color: #6d7d88;
  line-height: 1.7;
}

.login-form :deep(.el-form-item__label) {
  color: #52616d;
}

.login-form :deep(.el-input__wrapper) {
  min-height: 46px;
  border-radius: 0;
  box-shadow: 0 0 0 1px #d6e0e3 inset;
}

.login-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #5c8872 inset;
}

.login-submit {
  width: 100%;
  min-height: 46px;
  margin-top: 6px;
  border: none;
  border-radius: 0;
  background: linear-gradient(90deg, #4d8096 0%, #5e8b76 100%);
}

.login-panel-foot {
  display: flex;
  justify-content: flex-end;
  margin-top: 18px;
  padding-top: 18px;
  border-top: 1px solid #edf1f2;
}

.login-secondary-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  color: #426f87;
  cursor: pointer;
}

.login-secondary-link:hover {
  color: #2c5a73;
}

@keyframes fade-up {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 960px) {
  .login-shell {
    grid-template-columns: 1fr;
    gap: 24px;
  }

  .login-intro {
    justify-content: flex-start;
  }
}

@media (max-width: 640px) {
  .login-shell {
    padding: 18px;
  }

  .login-title {
    font-size: 34px;
  }

  .login-scope-grid {
    grid-template-columns: 1fr 1fr;
  }

  .login-panel {
    padding: 20px 18px;
  }
}
</style>
