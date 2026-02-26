<script setup lang="ts">
import { CollectionTag, Location, Management, Money, Setting, User } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "../stores/auth";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();

const canOpenAdminPanel = computed(() => auth.user?.role === "OWNER" || auth.user?.role === "ADMIN");

const menuItems = computed(() => {
  const items = [
    { path: "/leads", label: "客户开发", icon: Management },
    { path: "/customers", label: "客户列表", icon: User },
    { path: "/address-resources", label: "地址资源", icon: Location },
    { path: "/billing", label: "收费收款", icon: Money },
    { path: "/costs", label: "成本与老板视图", icon: CollectionTag },
  ];
  if (canOpenAdminPanel.value) {
    items.push({ path: "/admin/users", label: "管理员面板", icon: Setting });
  }
  return items;
});

function onMenuSelect(path: string) {
  router.push(path);
}

const activeMenu = computed(() => {
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
</script>

<template>
  <el-container class="app-shell">
    <el-aside width="220px" class="side-menu">
      <div class="logo">代账系统 MVP</div>
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
    <el-container>
      <el-header class="topbar">
        <div class="title">客户开发、管理、收款</div>
        <el-space>
          <el-tag type="info" effect="plain">
            <el-icon><User /></el-icon>
            &nbsp;{{ auth.user?.username ?? "未登录" }}（{{ roleLabel }}）
          </el-tag>
          <el-button size="small" @click="logout">退出</el-button>
        </el-space>
      </el-header>
      <el-main class="main-area">
        <router-view />
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
  height: 56px;
  border-bottom: 1px solid #e6e8eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
}

.title {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.main-area {
  background: #f7f8fa;
  padding: 16px;
}

@media (max-width: 900px) {
  .side-menu {
    width: 76px !important;
  }

  .logo {
    font-size: 12px;
    line-height: 1.2;
    padding: 14px 8px;
  }
}
</style>
