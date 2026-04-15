<script setup lang="ts">
import { ArrowRight } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";

import { getDefaultProtectedPath } from "../mobile/config";
import { startMobileLoginToTodoMeasurement } from "../mobile/metrics";
import { scheduleMobileWorkspacePrefetch } from "../mobile/prefetch";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const auth = useAuthStore();

const form = reactive({
  username: "",
  password: "",
});

const state = reactive({
  loading: false,
  ssoLoading: false,
  providersLoading: false,
});
const showLocalLogin = ref(false);

const scopeItems = ["客户开发", "客户列表", "收费明细", "到账核对"];
const providers = computed(() => auth.providers);
const ssoEnabled = computed(() => Boolean(providers.value?.sso.enabled));
const ssoLabel = computed(() => providers.value?.sso.label || "企业单点登录");
const localAdminOnly = computed(() => Boolean(providers.value?.local.admin_only));

async function login() {
  if (!form.username || !form.password) {
    ElMessage.warning("请输入账号和密码");
    return;
  }
  state.loading = true;
  try {
    await auth.login(form.username, form.password);
    startMobileLoginToTodoMeasurement();
    scheduleMobileWorkspacePrefetch();
    ElMessage.success("登录成功");
    router.push(getDefaultProtectedPath());
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "账号或密码错误");
  } finally {
    state.loading = false;
  }
}

function openPublicLibrary() {
  router.push("/library/public");
}

async function startSso() {
  state.ssoLoading = true;
  try {
    if (!auth.providers) {
      await auth.fetchProviders();
    }
    auth.startSsoLogin();
  } catch (error: any) {
    state.ssoLoading = false;
    ElMessage.error(error?.response?.data?.detail ?? "企业单点登录暂时不可用");
  }
}

onMounted(async () => {
  state.providersLoading = true;
  try {
    await auth.fetchProviders();
  } catch {
    ElMessage.warning("未能加载登录方式，先保留本地登录入口");
  } finally {
    state.providersLoading = false;
  }
});
</script>

<template>
  <section class="login-page">
    <div class="login-shell">
      <section class="login-intro">
        <div class="login-mark">账航 · 一帆财税</div>
        <h1 class="login-title">账航·一帆财税</h1>
        <p class="login-copy">客户开发、客户维护、收费明细、到账核对在同一套工作台里处理。</p>
        <div class="login-scope-strip">
          <span v-for="item in scopeItems" :key="item" class="login-scope-pill">{{ item }}</span>
        </div>
        <button class="login-secondary-link intro-link" @click="openPublicLibrary">
          查看公开资料
          <el-icon><ArrowRight /></el-icon>
        </button>
      </section>

      <section class="login-panel">
        <div class="login-panel-head">
          <div class="login-panel-title">登录</div>
          <div class="login-panel-copy">迁移期优先使用企业单点登录，本地账号仅保留给过渡期和应急管理员。</div>
        </div>

        <div class="sso-entry-block">
          <el-button
            class="login-submit"
            type="primary"
            :loading="state.ssoLoading || state.providersLoading"
            :disabled="!ssoEnabled && !state.providersLoading"
            @click="startSso"
          >
            {{ ssoEnabled ? ssoLabel : "企业单点登录未启用" }}
          </el-button>
          <div class="login-foot-note">统一账号、密码、MFA 和停用状态都由身份中心维护。</div>
        </div>

        <div class="local-login-toggle">
          <button class="login-secondary-link" type="button" @click="showLocalLogin = !showLocalLogin">
            {{ showLocalLogin ? "收起本地登录" : "展开本地登录" }}
          </button>
          <span class="local-login-note">
            {{ localAdminOnly ? "当前仅应急管理员支持本地登录" : "迁移期仍保留本地登录入口" }}
          </span>
        </div>

        <el-form v-if="showLocalLogin" :model="form" label-position="top" class="login-form" @submit.prevent="login">
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
          <el-button class="login-submit login-submit-local" type="default" :loading="state.loading" @click="login">
            本地账号进入系统
          </el-button>
        </el-form>

        <div class="login-panel-foot">
          <div class="login-foot-note">公开资料入口保留在系统外，企业单点登录完成后继续进入内部工作台。</div>
        </div>
      </section>
    </div>
  </section>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(180deg, var(--app-surface) 0%, var(--app-bg-soft) 100%);
}

.login-shell {
  min-height: 100vh;
  max-width: 1180px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 392px;
  gap: 28px;
  padding: clamp(20px, 3vw, 36px);
}

.login-intro,
.login-panel {
  opacity: 0;
  transform: translateY(12px);
  animation: fade-up 360ms ease forwards;
}

.login-intro {
  display: flex;
  flex-direction: column;
  justify-content: center;
  max-width: 620px;
}

.login-mark {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  padding: 6px 11px;
  border: 1px solid var(--app-border);
  background: var(--app-bg-soft);
  font-size: 12px;
  font-weight: 600;
  color: var(--app-accent-strong);
}

.login-title {
  margin: 18px 0 10px;
  font-size: clamp(32px, 4vw, 46px);
  line-height: 1.04;
  letter-spacing: -0.04em;
  color: var(--app-text-primary);
}

.login-copy {
  margin: 0;
  max-width: 480px;
  color: var(--app-text-muted);
  font-size: 15px;
  line-height: 1.7;
}

.login-scope-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 20px;
}

.login-scope-pill {
  padding: 8px 11px;
  border: 1px solid var(--app-border);
  background: var(--app-surface-muted);
  color: var(--app-text-secondary);
  font-size: 13px;
  font-weight: 600;
}

.intro-link {
  width: fit-content;
  margin-top: 16px;
  padding: 0;
}

.login-panel {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 24px;
  border: 1px solid var(--app-border);
  background: var(--app-surface);
  box-shadow: var(--app-shadow-soft);
  animation-delay: 80ms;
}

.login-panel-head {
  margin-bottom: 14px;
}

.login-panel-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.login-panel-copy {
  margin-top: 5px;
  color: var(--app-text-muted);
  line-height: 1.6;
  font-size: 13px;
}

.sso-entry-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.local-login-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--app-border-soft);
}

.local-login-note {
  color: var(--app-text-muted);
  font-size: 12px;
  line-height: 1.5;
  text-align: right;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 16px;
}

.login-form :deep(.el-form-item__label) {
  color: var(--app-text-muted);
  font-size: 13px;
}

.login-form :deep(.el-input__wrapper) {
  min-height: 44px;
  border-radius: 0;
  box-shadow: 0 0 0 1px var(--app-border) inset;
}

.login-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--app-accent-soft) inset;
}

.login-submit {
  width: 100%;
  min-height: 44px;
  margin-top: 2px;
  border: none;
  border-radius: 0;
  background: var(--app-gradient);
}

.login-submit-local {
  background: var(--app-surface-muted);
  color: var(--app-text-primary);
  border: 1px solid var(--app-border);
}

.login-panel-foot {
  display: flex;
  justify-content: flex-start;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--app-border-soft);
}

.login-foot-note {
  font-size: 12px;
  line-height: 1.6;
  color: var(--app-text-muted);
}

.login-secondary-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  color: var(--app-accent);
  cursor: pointer;
}

.login-secondary-link:hover {
  color: var(--app-accent-strong);
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
    gap: 20px;
  }

  .login-intro {
    justify-content: flex-start;
    max-width: none;
  }
}

@media (max-width: 640px) {
  .login-page {
    min-height: auto;
  }

  .login-shell {
    min-height: auto;
    gap: 14px;
    padding: 18px 18px 24px;
  }

  .login-title {
    margin-top: 12px;
    font-size: 34px;
  }

  .login-copy {
    font-size: 14px;
    line-height: 1.6;
  }

  .login-scope-strip {
    margin-top: 14px;
  }

  .login-scope-pill {
    padding: 7px 10px;
    font-size: 12px;
  }

  .intro-link {
    margin-top: 12px;
  }

  .login-panel {
    justify-content: flex-start;
    padding: 18px;
  }

  .local-login-toggle {
    align-items: flex-start;
    flex-direction: column;
  }

  .local-login-note {
    text-align: left;
  }
}
</style>
