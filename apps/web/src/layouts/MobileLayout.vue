<script setup lang="ts">
import {
  CollectionTag,
  Files,
  Grid,
  House,
  Location,
  Management,
  Money,
  MoreFilled,
  User,
} from "@element-plus/icons-vue";
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

import { getMobilePrimaryNavItems, getRoleLabel, resolveMobileBackPath } from "../mobile/config";
import { startMobilePrimaryNavMeasurement } from "../mobile/metrics";
import { prefetchMobileNavTarget } from "../mobile/prefetch";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();

const navIcons = {
  todo: House,
  leads: Management,
  customers: User,
  billing: Money,
  more: Grid,
} as const;

const sectionIcons = {
  "receipt-reconciliation": CollectionTag,
  "common-library": Files,
  "address-resources": Location,
  "admin-users": MoreFilled,
  costs: CollectionTag,
} as const;

const primaryNav = computed(() => getMobilePrimaryNavItems(auth.user));

const currentTitle = computed(() => String(route.meta.mobileTitle || "账航·一帆财税"));
const currentSubtitle = computed(() => String(route.meta.mobileSubtitle || ""));
const currentBackPath = computed(() => {
  const defaultBackPath = String(route.meta.mobileBackTo || "");
  const from = String(route.query.from || "");

  if (route.path.startsWith("/m/leads/")) {
    if (from === "customers") return "/m/customers";
    if (from.startsWith("customer:")) {
      const customerId = Number(from.split(":")[1]);
      if (customerId) return `/m/customers/${customerId}`;
    }
    return resolveMobileBackPath(defaultBackPath, "/m/leads");
  }

  if (route.path.startsWith("/m/customers/")) {
    if (from === "leads") return "/m/leads";
    return resolveMobileBackPath(defaultBackPath, "/m/customers");
  }

  return resolveMobileBackPath(defaultBackPath, "");
});
const isPrimaryRoute = computed(() => primaryNav.value.some((item) => route.path === item.path));
const currentPrimaryIcon = computed(() => {
  const navKey = String(route.meta.mobileNavKey || "todo");
  return navIcons[navKey as keyof typeof navIcons] || House;
});
const currentSectionIcon = computed(() => {
  const iconKey = String(route.meta.mobileIconKey || route.meta.mobileSectionKey || route.meta.mobileNavKey || "");
  return (
    navIcons[iconKey as keyof typeof navIcons] ||
    sectionIcons[iconKey as keyof typeof sectionIcons] ||
    House
  );
});

const userLabel = computed(() => {
  if (!auth.user) return "未登录";
  return `${auth.user.username} · ${getRoleLabel(auth.user)}`;
});

function isNavActive(path: string): boolean {
  if (path === "/m/todo") return route.path === "/m/todo";
  if (path === "/m/leads") return route.path.startsWith("/m/leads");
  if (path === "/m/customers") return route.path.startsWith("/m/customers");
  if (path === "/m/billing") return route.path.startsWith("/m/billing");
  if (path === "/m/more") return route.path.startsWith("/m/more");
  return route.path === path;
}

function goBack() {
  if (currentBackPath.value) {
    router.push(currentBackPath.value);
    return;
  }
  router.push("/m/todo");
}

function warmNavTarget(key: keyof typeof navIcons) {
  prefetchMobileNavTarget(key);
}

function navigateTo(path: string, label: string) {
  if (!isNavActive(path)) {
    startMobilePrimaryNavMeasurement({
      sourceLabel: currentTitle.value,
      sourcePath: route.path,
      targetLabel: label,
      targetPath: path,
    });
  }

  router.push(path);
}
</script>

<template>
  <div class="mobile-shell">
    <header class="mobile-shell-header">
      <div class="mobile-shell-header-inner">
        <div class="mobile-shell-topline">
          <button v-if="!isPrimaryRoute" class="mobile-shell-back" @click="goBack">返回</button>
          <div v-else class="mobile-shell-mark">账航 · 一帆财税</div>
          <div class="mobile-shell-user">{{ userLabel }}</div>
        </div>
        <div class="mobile-shell-heading">
          <div class="mobile-shell-title-block">
            <component :is="isPrimaryRoute ? currentPrimaryIcon : currentSectionIcon" class="mobile-shell-title-icon" />
            <div class="mobile-shell-title-copy">
              <div class="mobile-shell-title">{{ currentTitle }}</div>
              <div v-if="currentSubtitle" class="mobile-shell-copy">{{ currentSubtitle }}</div>
            </div>
          </div>
        </div>
      </div>
    </header>

    <main class="mobile-shell-main">
      <div class="mobile-shell-main-inner">
        <router-view v-slot="{ Component }">
          <transition name="mobile-screen" mode="out-in">
            <div :key="route.fullPath" class="mobile-screen-frame">
              <component :is="Component" />
            </div>
          </transition>
        </router-view>
      </div>
    </main>

    <nav class="mobile-shell-nav">
      <button
        v-for="item in primaryNav"
        :key="item.key"
        type="button"
        class="mobile-shell-nav-item"
        :class="{ active: isNavActive(item.path) }"
        @focus="warmNavTarget(item.key)"
        @pointerenter="warmNavTarget(item.key)"
        @touchstart.passive="warmNavTarget(item.key)"
        @click="navigateTo(item.path, item.label)"
      >
        <component :is="navIcons[item.key]" class="mobile-shell-nav-icon" />
        <span>{{ item.label }}</span>
      </button>
    </nav>
  </div>
</template>

<style scoped>
.mobile-shell {
  min-height: 100vh;
  background:
    radial-gradient(circle at top right, rgba(77, 128, 150, 0.12), transparent 34%),
    linear-gradient(180deg, var(--app-bg-soft) 0%, var(--app-bg) 100%);
  padding-bottom: calc(76px + env(safe-area-inset-bottom));
}

.mobile-shell-header {
  position: sticky;
  top: 0;
  z-index: 20;
  padding: max(12px, env(safe-area-inset-top)) 16px 14px;
  border-bottom: 1px solid var(--app-border-soft);
  background: rgba(250, 252, 252, 0.94);
  backdrop-filter: blur(14px);
}

.mobile-shell-header-inner,
.mobile-shell-main-inner {
  width: min(100%, 680px);
  margin: 0 auto;
}

.mobile-shell-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.mobile-shell-back,
.mobile-shell-mark,
.mobile-shell-user {
  font-size: 12px;
  line-height: 1.3;
}

.mobile-shell-back {
  border: none;
  padding: 0;
  background: transparent;
  color: var(--app-accent-strong);
}

.mobile-shell-mark,
.mobile-shell-user {
  color: var(--app-text-muted);
}

.mobile-shell-user {
  text-align: right;
}

.mobile-shell-heading {
  margin-top: 10px;
}

.mobile-shell-title-block {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.mobile-shell-title-copy {
  min-width: 0;
  flex: 1;
}

.mobile-shell-title-icon {
  width: 18px;
  height: 18px;
  display: block;
  font-size: 18px;
  color: var(--app-accent-strong);
  flex-shrink: 0;
}

.mobile-shell-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.mobile-shell-copy {
  margin-top: 2px;
  font-size: 12px;
  color: var(--app-text-muted);
}

.mobile-shell-main {
  padding: 14px 16px 0;
}

.mobile-screen-frame {
  min-width: 0;
}

.mobile-shell-nav {
  position: fixed;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 30;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 4px;
  padding: 8px 12px calc(8px + env(safe-area-inset-bottom));
  border-top: 1px solid var(--app-border-soft);
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(12px);
}

.mobile-shell-nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  border: none;
  border-radius: 12px;
  background: transparent;
  color: var(--app-text-muted);
  min-height: 48px;
  padding: 6px 4px 5px;
  font-size: 11px;
}

.mobile-shell-nav-item.active {
  background: rgba(77, 128, 150, 0.12);
  color: var(--app-accent-strong);
}

.mobile-shell-nav-icon {
  width: 18px;
  height: 18px;
  display: block;
  color: currentColor;
  flex-shrink: 0;
}

.mobile-screen-enter-active,
.mobile-screen-leave-active {
  transition: opacity 180ms ease, transform 180ms ease;
}

.mobile-screen-enter-from,
.mobile-screen-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
