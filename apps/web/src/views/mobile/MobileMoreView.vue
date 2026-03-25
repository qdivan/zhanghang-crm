<script setup lang="ts">
import { ArrowRight, CollectionTag, Files, Location, Money, Setting, SwitchButton } from "@element-plus/icons-vue";
import { ElMessageBox } from "element-plus";
import { computed } from "vue";
import { useRouter } from "vue-router";

import { getMobileMoreSections, getRoleLabel } from "../../mobile/config";
import { useAuthStore } from "../../stores/auth";

const auth = useAuthStore();
const router = useRouter();

const entryIcons = {
  "receipt-reconciliation": Money,
  "common-library": Files,
  "address-resources": Location,
  "admin-users": Setting,
  costs: CollectionTag,
} as const;

const moreSections = computed(() => getMobileMoreSections(auth.user));
const profileSignals = computed(() => {
  if (!auth.user) return [];
  const grantedModules = auth.user.granted_read_modules.length
    ? auth.user.granted_read_modules.map((item) => (item === "BILLING" ? "收费" : "客户")).join(" / ")
    : "无额外授权";

  let scope = "个人名下";
  if (auth.user.role === "OWNER") scope = "全局视图";
  else if (auth.user.role === "ADMIN") scope = "后台管理";
  else if (auth.user.role === "MANAGER") scope = "团队范围";
  else if (auth.user.granted_read_modules.length) scope = "带授权访问";

  return [
    { label: "认证", value: auth.user.auth_source === "LDAP" ? "LDAP" : "本地账号" },
    { label: "数据范围", value: scope },
    { label: "附加授权", value: grantedModules },
  ];
});

function resolveEntryIcon(key: string) {
  return entryIcons[key as keyof typeof entryIcons] || Files;
}

async function logout() {
  try {
    await ElMessageBox.confirm("确认退出当前账号吗？", "退出登录", {
      type: "warning",
      confirmButtonText: "退出",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  auth.logout();
  router.push("/login");
}
</script>

<template>
  <section class="mobile-page mobile-more-page">
    <section class="mobile-profile-block">
      <div class="mobile-profile-mark">账航 · 一帆财税</div>
      <div class="mobile-profile-name">{{ auth.user?.username || "未登录" }}</div>
      <div class="mobile-profile-role">{{ getRoleLabel(auth.user) }}</div>
      <div v-if="profileSignals.length" class="mobile-profile-signal-grid">
        <div v-for="item in profileSignals" :key="item.label" class="mobile-profile-signal">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </div>
      </div>
    </section>

    <section
      v-for="section in moreSections"
      :key="section.key"
      class="mobile-more-section"
    >
      <div class="mobile-more-title">{{ section.label }}</div>
      <div class="mobile-more-copy">{{ section.description }}</div>
      <button
        v-for="entry in section.entries"
        :key="entry.key"
        type="button"
        class="mobile-more-entry"
        @click="router.push(entry.path)"
      >
        <div class="mobile-more-entry-main">
          <component :is="resolveEntryIcon(entry.key)" class="mobile-more-entry-icon" />
          <div>
            <div class="mobile-more-entry-title">{{ entry.label }}</div>
            <div class="mobile-more-entry-copy">{{ entry.description }}</div>
          </div>
        </div>
        <el-icon class="mobile-more-entry-arrow"><ArrowRight /></el-icon>
      </button>
    </section>

    <section class="mobile-more-section">
      <div class="mobile-more-title">账户</div>
      <button type="button" class="mobile-more-entry danger" @click="logout">
        <div class="mobile-more-entry-main">
          <el-icon class="mobile-more-entry-icon"><SwitchButton /></el-icon>
          <div>
            <div class="mobile-more-entry-title">退出登录</div>
            <div class="mobile-more-entry-copy">退出当前账号。</div>
          </div>
        </div>
        <el-icon class="mobile-more-entry-arrow"><ArrowRight /></el-icon>
      </button>
    </section>
  </section>
</template>

<style scoped>
.mobile-more-page {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.mobile-profile-block,
.mobile-more-section {
  border: 1px solid var(--app-border-soft);
  background: rgba(255, 255, 255, 0.9);
  box-shadow: var(--app-shadow-soft);
  padding: 14px;
}

.mobile-profile-mark {
  font-size: 12px;
  color: var(--app-text-muted);
}

.mobile-profile-name {
  margin-top: 10px;
  font-size: 22px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.mobile-profile-role {
  margin-top: 4px;
  font-size: 13px;
  color: var(--app-accent-strong);
}

.mobile-profile-signal-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 14px;
}

.mobile-profile-signal {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px;
  border: 1px solid var(--app-border-soft);
  background: var(--app-bg-soft);
}

.mobile-profile-signal span {
  font-size: 11px;
  color: var(--app-text-muted);
}

.mobile-profile-signal strong {
  font-size: 12px;
  line-height: 1.45;
  color: var(--app-text-primary);
}

.mobile-more-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.mobile-more-copy {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--app-text-muted);
}

.mobile-more-entry {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  padding: 14px 0;
  border: none;
  border-top: 1px solid var(--app-border-soft);
  background: transparent;
  text-align: left;
}

.mobile-more-entry-main {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
}

.mobile-more-entry:first-of-type {
  margin-top: 10px;
}

.mobile-more-entry-icon {
  margin-top: 2px;
  font-size: 18px;
  color: var(--app-accent-strong);
  flex-shrink: 0;
}

.mobile-more-entry-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--app-text-primary);
}

.mobile-more-entry-copy {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--app-text-muted);
}

.mobile-more-entry-arrow {
  color: #9aa7af;
}

.mobile-more-entry.danger .mobile-more-entry-icon,
.mobile-more-entry.danger .mobile-more-entry-title {
  color: #b54848;
}
</style>
