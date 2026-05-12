<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { getDefaultProtectedPath } from "../mobile/config";
import { useAuthStore } from "../stores/auth";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const loading = ref(true);
const title = ref("正在完成企业单点登录");
const copy = ref("请稍候，我们正在校验企业身份并准备进入工作台。");
const showBack = ref(false);

const ticket = computed(() => String(route.query.ticket || "").trim());

async function finishSso() {
  if (!ticket.value) {
    loading.value = false;
    title.value = "企业单点登录未完成";
    copy.value = "缺少登录票据，请返回登录页重新发起企业单点登录。";
    showBack.value = true;
    return;
  }
  try {
    const result = await auth.exchangeSsoTicket(ticket.value);
    if (result.status === "SUCCESS") {
      ElMessage.success(result.message || "企业单点登录成功");
      await router.replace(getDefaultProtectedPath(auth.user));
      return;
    }
    if (result.status === "PENDING_BINDING") {
      title.value = "账号待管理员确认绑定";
      copy.value = result.message || "当前企业账号需要管理员在后台确认绑定后才能进入 CRM。";
      showBack.value = true;
      return;
    }
    title.value = "企业单点登录失败";
    copy.value = result.message || "企业单点登录未完成，请稍后重试。";
    showBack.value = true;
  } catch (error: any) {
    title.value = "企业单点登录失败";
    copy.value = error?.response?.data?.detail ?? error?.response?.data?.message ?? "票据已失效，请重新发起登录。";
    showBack.value = true;
  } finally {
    loading.value = false;
  }
}

function backToLogin() {
  router.replace("/login");
}

onMounted(() => {
  void finishSso();
});
</script>

<template>
  <section class="login-page">
    <div class="login-shell sso-shell">
      <section class="login-intro">
        <div class="login-mark">账航 · 一帆财税</div>
        <h1 class="login-title">{{ title }}</h1>
        <p class="login-copy">{{ copy }}</p>
        <button v-if="showBack" class="login-secondary-link intro-link" @click="backToLogin">
          返回登录页
        </button>
      </section>

      <section class="login-panel sso-panel">
        <div class="login-panel-head">
          <div class="login-panel-title">企业单点登录</div>
          <div class="login-panel-copy">CRM 会在认证成功后继续签发自己的业务令牌。</div>
        </div>
        <div class="sso-status-box">
          <div class="sso-status-dot" :class="{ spinning: loading }" />
          <div class="sso-status-text">
            <strong>{{ loading ? "处理中" : "已完成" }}</strong>
            <span>{{ copy }}</span>
          </div>
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
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.login-mark {
  display: inline-flex;
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

.login-panel {
  padding: 24px;
  border: 1px solid var(--app-border);
  background: var(--app-surface);
  box-shadow: var(--app-shadow-soft);
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

.login-secondary-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  color: var(--app-accent);
  cursor: pointer;
  padding: 0;
  margin-top: 16px;
}

.login-secondary-link:hover {
  color: var(--app-accent-strong);
}

.sso-shell {
  align-items: center;
}

.sso-panel {
  justify-content: center;
}

.sso-status-box {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px;
  border: 1px solid var(--app-border);
  background: var(--app-surface-muted);
}

.sso-status-dot {
  width: 12px;
  height: 12px;
  border-radius: 999px;
  background: var(--app-accent);
  box-shadow: 0 0 0 6px rgba(62, 131, 255, 0.12);
}

.sso-status-dot.spinning {
  animation: pulse 1.1s ease-in-out infinite;
}

.sso-status-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: var(--app-text-secondary);
  font-size: 13px;
}

.sso-status-text strong {
  color: var(--app-text-primary);
  font-size: 14px;
}

@keyframes pulse {
  0%,
  100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(0.85);
    opacity: 0.65;
  }
}

@media (max-width: 960px) {
  .login-shell {
    grid-template-columns: 1fr;
    gap: 20px;
  }
}

@media (max-width: 640px) {
  .login-shell {
    min-height: auto;
    gap: 14px;
    padding: 18px 18px 24px;
  }

  .login-panel {
    padding: 18px;
  }
}
</style>
