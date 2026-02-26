<script setup lang="ts">
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
  } catch (error) {
    ElMessage.error("账号或密码错误");
  } finally {
    state.loading = false;
  }
}
</script>

<template>
  <div class="login-wrap">
    <el-card class="login-card" shadow="never">
      <template #header>
        <div class="head">
          <div class="title">代账系统登录</div>
          <div class="subtitle">本地账号（LDAP 二期接入）</div>
          <div class="hint">演示账号：boss / admin / accountant，密码均为 Demo@12345</div>
        </div>
      </template>
      <el-form :model="form" label-position="top" @submit.prevent="login">
        <el-form-item label="账号">
          <el-input v-model="form.username" placeholder="请输入账号" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="请输入密码"
          />
        </el-form-item>
        <el-button
          type="primary"
          style="width: 100%"
          :loading="state.loading"
          @click="login"
        >
          登录
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.login-wrap {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #f2f7ff 0%, #f8fbf5 100%);
  padding: 16px;
}

.login-card {
  width: min(420px, 100%);
}

.head {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.title {
  font-size: 20px;
  font-weight: 700;
}

.subtitle {
  font-size: 13px;
  color: #6b7280;
}

.hint {
  font-size: 12px;
  color: #9ca3af;
}
</style>
