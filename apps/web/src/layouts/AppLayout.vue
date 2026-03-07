<script setup lang="ts">
import {
  CollectionTag,
  House,
  Location,
  Management,
  Menu as MenuIcon,
  Money,
  Setting,
  User,
} from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "../stores/auth";
import TodoDock from "../components/TodoDock.vue";
import { useResponsive } from "../composables/useResponsive";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const { isMobile } = useResponsive();
const mobileMenuVisible = ref(false);

const canOpenAdminPanel = computed(() => auth.user?.role === "OWNER" || auth.user?.role === "ADMIN");
const canOpenCostView = computed(() => auth.user?.role === "OWNER");

const menuItems = computed(() => {
  const items = [
    { path: "/dashboard", label: "工作台", icon: House },
    { path: "/leads", label: "客户开发", icon: Management },
    { path: "/customers", label: "客户列表", icon: User },
    { path: "/address-resources", label: "地址资源", icon: Location },
    { path: "/billing", label: "收费收款", icon: Money },
  ];
  if (canOpenCostView.value) {
    items.push({ path: "/costs", label: "成本与老板视图", icon: CollectionTag });
  }
  if (canOpenAdminPanel.value) {
    items.push({ path: "/admin/users", label: "管理员面板", icon: Setting });
  }
  return items;
});

function onMenuSelect(path: string) {
  router.push(path);
  mobileMenuVisible.value = false;
}

const activeMenu = computed(() => {
  if (route.path.startsWith("/dashboard")) return "/dashboard";
  if (route.path.startsWith("/leads")) return "/leads";
  if (route.path.startsWith("/customers")) return "/customers";
  if (route.path.startsWith("/address-resources")) return "/address-resources";
  if (route.path.startsWith("/billing")) return "/billing";
  if (route.path.startsWith("/costs")) return "/costs";
  if (route.path.startsWith("/admin")) return "/admin/users";
  return route.path;
});

const roleLabel = computed(() => {
  if (!auth.user) return "-";
  if (auth.user.role === "OWNER") return "老板";
  if (auth.user.role === "ADMIN") return "管理员";
  return "会计";
});

function logout() {
  auth.logout();
  ElMessage.success("已退出登录");
  router.push("/login");
}

watch(
  () => route.fullPath,
  () => {
    mobileMenuVisible.value = false;
  },
);

watch(isMobile, (value) => {
  if (!value) {
    mobileMenuVisible.value = false;
  }
});

const userTagText = computed(() => {
  const username = auth.user?.username ?? "未登录";
  return isMobile.value ? username : `${username}（${roleLabel.value}）`;
});
</script>

<template>
  <el-container class="app-shell">
    <el-aside v-if="!isMobile" width="220px" class="side-menu">
      <div class="logo">账航·一帆财税</div>
      <el-menu
        :default-active="activeMenu"
        class="menu"
        @select="onMenuSelect"
      >
        <el-menu-item
          v-for="item in menuItems"
          :key="item.path"
          :index="item.path"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-drawer
      v-if="isMobile"
      v-model="mobileMenuVisible"
      direction="ltr"
      size="240px"
      :with-header="false"
      class="mobile-menu-drawer"
    >
      <div class="logo">账航·一帆财税</div>
      <el-menu
        :default-active="activeMenu"
        class="menu"
        @select="onMenuSelect"
      >
        <el-menu-item
          v-for="item in menuItems"
          :key="item.path"
          :index="item.path"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>
    </el-drawer>
    <el-container>
      <el-header class="topbar">
        <div class="top-left">
          <el-button v-if="isMobile" circle plain size="small" @click="mobileMenuVisible = true">
            <el-icon><MenuIcon /></el-icon>
          </el-button>
          <div class="brand-block">
            <div class="title">账航·一帆财税</div>
            <div class="subtitle">客户开发、管理、收款</div>
          </div>
        </div>
        <div class="top-right">
          <el-tag type="info" effect="plain" class="user-tag">
            <el-icon><User /></el-icon>
            <span class="user-tag-text">{{ userTagText }}</span>
          </el-tag>
          <el-button size="small" @click="logout">退出</el-button>
        </div>
      </el-header>
      <el-main class="main-area">
        <div class="content-main">
          <router-view />
        </div>
        <TodoDock />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
}

.side-menu {
  border-right: 1px solid #e6e8eb;
  background: #fff;
}

.logo {
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
  padding: 18px 16px;
  border-bottom: 1px solid #f1f3f5;
}

.menu {
  border-right: none;
}

.topbar {
  min-height: 56px;
  border-bottom: 1px solid #e6e8eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  padding: 0 12px;
}

.top-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.brand-block {
  min-width: 0;
}

.top-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  min-width: 0;
  flex-shrink: 0;
}

.user-tag {
  max-width: 240px;
}

.user-tag-text {
  display: inline-block;
  max-width: 190px;
  margin-left: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}

.title {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.subtitle {
  font-size: 12px;
  color: #6b7280;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.main-area {
  background: #f7f8fa;
  padding: 16px;
  overflow-x: hidden;
}

.content-main {
  min-width: 0;
  overflow-x: visible;
}

@media (max-width: 900px) {
  .topbar {
    padding: 8px;
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 8px;
  }

  .top-left {
    flex: 1;
    min-width: 0;
  }

  .top-right {
    width: 100%;
    max-width: none;
    gap: 6px;
    justify-content: space-between;
  }

  .user-tag {
    max-width: none;
    flex: 1;
  }

  .user-tag-text {
    max-width: 100%;
  }

  .title {
    font-size: 14px;
  }

  .subtitle {
    display: none;
  }

  .main-area {
    padding: 10px 10px 78px;
  }
}

.topbar :deep(.el-tag__content) {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  white-space: nowrap;
}
</style>
