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
    <section class="public-library-hero">
      <div class="public-library-back">
        <RouterLink to="/login" class="public-link">
          <el-icon><ArrowLeft /></el-icon>
          <span>返回登录</span>
        </RouterLink>
      </div>

      <div class="public-library-hero-inner">
        <div class="public-library-brand">账航·一帆财税</div>
        <h1 class="public-library-title">公开资料库</h1>
        <p class="public-library-copy">
          这里放可以直接给客户看的模板、资料清单和办事说明。内部方法仍留在系统内维护。
        </p>
      </div>
    </section>

    <main class="public-library-main">
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
    </main>
  </div>
</template>

<style scoped>
.public-library-page {
  min-height: 100vh;
  background:
    radial-gradient(circle at 12% 18%, rgba(230, 175, 72, 0.14), transparent 34%),
    radial-gradient(circle at 82% 22%, rgba(113, 173, 198, 0.18), transparent 28%),
    linear-gradient(180deg, #081a26 0%, #0d2230 38%, #f4efe6 38%, #f4efe6 100%);
  color: #10202f;
}

.public-library-hero {
  padding: 28px 32px 40px;
  color: #f4efe6;
}

.public-library-back {
  margin-bottom: 48px;
}

.public-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: rgba(244, 239, 230, 0.82);
  text-decoration: none;
}

.public-link:hover {
  color: #ffffff;
}

.public-library-hero-inner {
  max-width: 720px;
}

.public-library-brand {
  font-family: "Songti SC", "STSong", "Noto Serif CJK SC", serif;
  font-size: 16px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: rgba(244, 239, 230, 0.66);
}

.public-library-title {
  margin: 14px 0 10px;
  font-family: "Songti SC", "STSong", "Noto Serif CJK SC", serif;
  font-size: clamp(40px, 8vw, 76px);
  line-height: 0.98;
  letter-spacing: -0.03em;
}

.public-library-copy {
  max-width: 500px;
  margin: 0;
  color: rgba(244, 239, 230, 0.8);
  font-size: 15px;
  line-height: 1.8;
}

.public-library-main {
  padding: 28px 32px 56px;
}

.public-library-toolbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 28px;
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
  border: 1px solid rgba(16, 32, 47, 0.12);
  background: rgba(255, 255, 255, 0.62);
  color: #254053;
  border-radius: 999px;
  padding: 9px 14px;
  cursor: pointer;
  transition: transform 160ms ease, background-color 160ms ease, color 160ms ease, border-color 160ms ease;
}

.public-tab:hover {
  transform: translateY(-1px);
  border-color: rgba(16, 32, 47, 0.24);
}

.public-tab.active {
  background: #10202f;
  color: #f4efe6;
  border-color: #10202f;
}

.public-library-list {
  padding-top: 12px;
}

.public-library-list-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(16, 32, 47, 0.12);
}

.public-library-section-title {
  font-family: "Songti SC", "STSong", "Noto Serif CJK SC", serif;
  font-size: 28px;
  line-height: 1.1;
}

.public-library-section-copy {
  margin-top: 8px;
  color: #596b79;
  font-size: 13px;
}

.public-library-count {
  color: #596b79;
  font-size: 13px;
}

.public-empty {
  padding: 28px 0;
  color: #596b79;
  font-size: 14px;
}

.public-article {
  padding: 22px 0;
  border-bottom: 1px solid rgba(16, 32, 47, 0.1);
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
  background: rgba(16, 32, 47, 0.08);
  color: #163042;
  padding: 4px 10px;
  font-size: 12px;
}

.public-category {
  color: #6a7885;
  font-size: 12px;
}

.public-article-title {
  margin: 0;
  font-size: 24px;
  line-height: 1.25;
  color: #10202f;
}

.public-article-content {
  max-width: 860px;
  margin: 12px 0 0;
  color: #314552;
  line-height: 1.8;
}

.public-article-contact,
.public-article-note {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 12px;
  color: #596b79;
  font-size: 13px;
}

@media (max-width: 900px) {
  .public-library-hero,
  .public-library-main {
    padding-left: 18px;
    padding-right: 18px;
  }

  .public-library-back {
    margin-bottom: 28px;
  }

  .public-library-toolbar,
  .public-library-list-head {
    flex-direction: column;
    align-items: stretch;
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

  .public-library-section-title {
    font-size: 24px;
  }

  .public-article-title {
    font-size: 20px;
  }
}
</style>
