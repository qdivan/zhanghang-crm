<script setup lang="ts">
import { ArrowLeft, Search } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";

import { apiClient } from "../api/client";
import type { CommonLibraryItem, CommonLibraryModuleType } from "../types";

type PublicModuleMeta = {
  label: string;
  helper: string;
};

const rows = ref<CommonLibraryItem[]>([]);
const loading = ref(false);
const keyword = ref("");
const activeTab = ref<CommonLibraryModuleType | "ALL">("ALL");

const moduleMetaMap: Record<CommonLibraryModuleType, PublicModuleMeta> = {
  TEMPLATE: {
    label: "常用模板",
    helper: "适合直接复制给客户的标准话术与资料清单。",
  },
  DIRECTORY: {
    label: "通讯录模板",
    helper: "税局、审批局、人社局、银行等常用联系方式。",
  },
  EXTENSION_A: {
    label: "公开方法",
    helper: "对外可用的方法、条件和基础说明。",
  },
  EXTENSION_B: {
    label: "公开资料",
    helper: "可给客户直接查看或复制的资料内容。",
  },
  EXTENSION_C: {
    label: "扩展资料",
    helper: "预留的公开资料模块。",
  },
};

const visibleRows = computed(() => {
  if (activeTab.value === "ALL") return rows.value;
  return rows.value.filter((item) => item.module_type === activeTab.value);
});

async function fetchPublicItems() {
  loading.value = true;
  try {
    const resp = await apiClient.get<CommonLibraryItem[]>("/common-library-items/public", {
      params: {
        keyword: keyword.value || undefined,
      },
    });
    rows.value = resp.data;
  } catch {
    ElMessage.error("加载公开资料失败");
  } finally {
    loading.value = false;
  }
}

watch(keyword, () => {
  window.clearTimeout((fetchPublicItems as any)._timer);
  (fetchPublicItems as any)._timer = window.setTimeout(fetchPublicItems, 200);
});

onMounted(fetchPublicItems);
</script>

<template>
  <div class="public-library-page">
    <section class="public-library-shell">
      <header class="public-library-topbar">
        <RouterLink to="/login" class="public-link">
          <el-icon><ArrowLeft /></el-icon>
          <span>返回登录</span>
        </RouterLink>
        <div class="public-library-brandmark">账航·一帆财税</div>
      </header>

      <section class="public-library-intro">
        <div class="public-library-intro-copy">
          <div class="public-library-eyebrow">公开资料</div>
          <h1 class="public-library-title">公开资料库</h1>
          <p class="public-library-copy">
            放可以直接发给客户的模板、资料清单和基础说明。内部方法继续留在系统内维护。
          </p>
        </div>
        <div class="public-library-intro-meta">
          <div class="public-library-stat">
            <span class="public-library-stat-label">当前公开条目</span>
            <strong class="public-library-stat-value">{{ rows.length }}</strong>
          </div>
          <div class="public-library-stat-note">只展示已标记为“可公开到官网”的内容。</div>
        </div>
      </section>

      <section class="public-library-toolbar">
        <div class="public-library-search">
          <el-input
            v-model="keyword"
            clearable
            placeholder="搜索标题、分类、内容"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>
        <div class="public-library-tabs">
          <button
            class="public-tab"
            :class="{ active: activeTab === 'ALL' }"
            @click="activeTab = 'ALL'"
          >
            全部
          </button>
          <button
            v-for="(meta, key) in moduleMetaMap"
            :key="key"
            class="public-tab"
            :class="{ active: activeTab === key }"
            @click="activeTab = key"
          >
            {{ meta.label }}
          </button>
        </div>
      </section>

      <section class="public-library-list" v-loading="loading">
        <div class="public-library-list-head">
          <div>
            <div class="public-library-section-title">
              {{ activeTab === "ALL" ? "全部公开内容" : moduleMetaMap[activeTab].label }}
            </div>
            <div class="public-library-section-copy">
              {{
                activeTab === "ALL"
                  ? "当前展示所有标记为“可公开到官网”的内容。"
                  : moduleMetaMap[activeTab].helper
              }}
            </div>
          </div>
          <div class="public-library-count">{{ visibleRows.length }} 条</div>
        </div>

        <div v-if="visibleRows.length === 0" class="public-empty">
          当前没有可展示的公开资料。
        </div>

        <article
          v-for="row in visibleRows"
          :key="row.id"
          class="public-article"
        >
          <div class="public-article-meta">
            <span class="public-badge">{{ moduleMetaMap[row.module_type].label }}</span>
            <span class="public-category">{{ row.category || "未分类" }}</span>
          </div>
          <h2 class="public-article-title">{{ row.title || row.category || "公开资料" }}</h2>
          <p v-if="row.content" class="public-article-content">{{ row.content }}</p>
          <div v-if="row.phone || row.address" class="public-article-contact">
            <span v-if="row.phone">电话：{{ row.phone }}</span>
            <span v-if="row.address">地址：{{ row.address }}</span>
          </div>
          <div v-if="row.notes" class="public-article-note">补充：{{ row.notes }}</div>
        </article>
      </section>
    </section>
  </div>
</template>

<style scoped>
.public-library-page {
  min-height: 100vh;
  background:
    radial-gradient(circle at top left, rgba(93, 138, 160, 0.09), transparent 24%),
    linear-gradient(180deg, #f7fafb 0%, #f4f6f8 100%);
  color: #1f2937;
}

.public-library-shell {
  width: min(1180px, calc(100vw - 48px));
  margin: 0 auto;
  padding: 24px 0 48px;
}

.public-library-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.public-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #53707f;
  text-decoration: none;
  font-size: 14px;
}

.public-link:hover {
  color: #264653;
}

.public-library-brandmark {
  border-radius: 999px;
  background: #eef3f5;
  border: 1px solid #dde7eb;
  color: #365868;
  padding: 7px 12px;
  font-size: 13px;
  font-weight: 600;
}

.public-library-intro {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(240px, 0.8fr);
  gap: 18px;
  align-items: stretch;
  margin-bottom: 16px;
}

.public-library-intro-copy,
.public-library-intro-meta,
.public-library-toolbar,
.public-library-list {
  border: 1px solid #e5eaee;
  background: rgba(255, 255, 255, 0.92);
  border-radius: 18px;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.04);
}

.public-library-intro-copy {
  padding: 22px 24px;
}

.public-library-eyebrow {
  color: #5c7b88;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.public-library-title {
  margin: 10px 0 8px;
  font-size: clamp(34px, 4vw, 52px);
  line-height: 1.04;
  letter-spacing: -0.03em;
  color: #132634;
}

.public-library-copy {
  max-width: 620px;
  margin: 0;
  color: #60717e;
  font-size: 14px;
  line-height: 1.7;
}

.public-library-intro-meta {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 22px 24px;
  background: linear-gradient(180deg, rgba(247, 250, 251, 0.98), rgba(241, 246, 248, 0.98));
}

.public-library-stat {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.public-library-stat-label {
  color: #6d808d;
  font-size: 12px;
}

.public-library-stat-value {
  font-size: 34px;
  line-height: 1;
  color: #183546;
}

.public-library-stat-note {
  color: #718391;
  font-size: 12px;
  line-height: 1.6;
}

.public-library-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  padding: 16px 18px;
}

.public-library-search {
  width: min(360px, 100%);
}

.public-library-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.public-tab {
  border: 1px solid #d9e3e8;
  background: #f7fafb;
  color: #476473;
  border-radius: 999px;
  padding: 8px 13px;
  cursor: pointer;
  transition: border-color 160ms ease, background-color 160ms ease, color 160ms ease;
}

.public-tab:hover {
  border-color: #9cb4bf;
  color: #2e4d5d;
}

.public-tab.active {
  background: #2e5563;
  color: #f8fbfc;
  border-color: #2e5563;
}

.public-library-list {
  padding: 18px 20px 8px;
}

.public-library-list-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid #e8edf0;
}

.public-library-section-title {
  font-size: 24px;
  line-height: 1.15;
  font-weight: 700;
  color: #1c3140;
}

.public-library-section-copy {
  margin-top: 6px;
  color: #677884;
  font-size: 13px;
}

.public-library-count {
  color: #6a7e8b;
  font-size: 13px;
}

.public-empty {
  padding: 28px 2px;
  color: #6b7c88;
  font-size: 14px;
}

.public-article {
  padding: 18px 2px;
  border-bottom: 1px solid #edf1f3;
}

.public-article-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.public-badge {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  background: #edf4f6;
  color: #305261;
  padding: 4px 10px;
  font-size: 12px;
}

.public-category {
  color: #738490;
  font-size: 12px;
}

.public-article-title {
  margin: 0;
  font-size: 22px;
  line-height: 1.25;
  color: #183243;
}

.public-article-content {
  max-width: 860px;
  margin: 10px 0 0;
  color: #364955;
  line-height: 1.8;
}

.public-article-contact,
.public-article-note {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 12px;
  color: #61737f;
  font-size: 13px;
}

@media (max-width: 900px) {
  .public-library-shell {
    width: calc(100vw - 24px);
    padding: 16px 0 28px;
  }

  .public-library-topbar,
  .public-library-toolbar,
  .public-library-list-head {
    flex-direction: column;
    align-items: stretch;
  }

  .public-library-intro {
    grid-template-columns: 1fr;
  }

  .public-library-intro-copy,
  .public-library-intro-meta,
  .public-library-toolbar,
  .public-library-list {
    border-radius: 16px;
  }

  .public-library-intro-copy,
  .public-library-intro-meta,
  .public-library-toolbar {
    padding-left: 16px;
    padding-right: 16px;
  }

  .public-library-title {
    font-size: 34px;
  }

  .public-library-search {
    width: 100%;
  }

  .public-library-tabs {
    overflow-x: auto;
    flex-wrap: nowrap;
    padding-bottom: 4px;
  }

  .public-tab {
    white-space: nowrap;
  }

  .public-library-list {
    padding: 16px;
  }

  .public-library-section-title {
    font-size: 20px;
  }

  .public-article-title {
    font-size: 18px;
  }
}
</style>
