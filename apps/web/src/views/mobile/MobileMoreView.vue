<script setup lang="ts">
import { ArrowRight, CollectionTag, Files, Location, Money, Setting, SwitchButton } from "@element-plus/icons-vue";
import { ElMessageBox } from "element-plus";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import { getMobileMoreSections, getRoleLabel } from "../../mobile/config";
import {
  clearMobilePerformanceEntries,
  readMobilePerformanceEntries,
  subscribeMobilePerformanceEntries,
  type MobilePerformanceEntry,
} from "../../mobile/metrics";
import { prefetchMobileMoreEntry, prefetchMobileRoutePath } from "../../mobile/prefetch";
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
const performanceEntries = ref<MobilePerformanceEntry[]>([]);
type PerformanceStatusTone = "success" | "warning" | "danger" | "info";
type PerformanceStatus = {
  label: "待观察" | "正常" | "偏慢" | "需要预热";
  tone: PerformanceStatusTone;
  note: string;
  shouldWarm: boolean;
};
type NavPerformanceInsight = {
  path: string;
  label: string;
  totalMs: number;
  count: number;
  latestMs: number;
  averageMs: number;
  status: PerformanceStatus;
};
type BaselinePathInsight = {
  key: string;
  label: string;
  sourcePath: string;
  targetPath: string;
  entries: MobilePerformanceEntry[];
  count: number;
  latestMs: number | null;
  averageMs: number | null;
  recordedAt: string;
  status: PerformanceStatus;
  warmable: boolean;
};
type BaselineConclusion = {
  title: string;
  note: string;
  status: PerformanceStatus;
  actionPath: string | null;
  actionLabel: string;
};

const baselineDefinitions = [
  {
    key: "login-todo",
    label: "登录 -> Todo",
    kind: "login_to_todo" as const,
    sourcePath: "/login",
    targetPath: "/m/todo",
    warmable: false,
    statusKind: "login" as const,
  },
  {
    key: "todo-leads",
    label: "Todo -> 开发",
    kind: "primary_nav" as const,
    sourcePath: "/m/todo",
    targetPath: "/m/leads",
    warmable: true,
    statusKind: "nav" as const,
  },
  {
    key: "todo-customers",
    label: "Todo -> 客户",
    kind: "primary_nav" as const,
    sourcePath: "/m/todo",
    targetPath: "/m/customers",
    warmable: true,
    statusKind: "nav" as const,
  },
  {
    key: "todo-billing",
    label: "Todo -> 收费",
    kind: "primary_nav" as const,
    sourcePath: "/m/todo",
    targetPath: "/m/billing",
    warmable: true,
    statusKind: "nav" as const,
  },
  {
    key: "todo-more",
    label: "Todo -> 更多",
    kind: "primary_nav" as const,
    sourcePath: "/m/todo",
    targetPath: "/m/more",
    warmable: true,
    statusKind: "nav" as const,
  },
] as const;

const loginPerformanceSummary = computed(() => {
  const entries = performanceEntries.value.filter((item) => item.kind === "login_to_todo");
  const latestEntry = entries[entries.length - 1];
  const fastestMs = entries.length
    ? Math.min(...entries.map((item) => item.durationMs))
    : null;

  return {
    count: entries.length,
    latestMs: latestEntry?.durationMs ?? null,
    fastestMs,
    recordedAt: latestEntry?.recordedAt ?? "",
  };
});

const navPerformanceEntries = computed(() => performanceEntries.value.filter((item) => item.kind === "primary_nav"));

const navPerformanceSummary = computed(() => {
  const entries = navPerformanceEntries.value;
  const latestEntry = entries[entries.length - 1];
  const averageMs = entries.length
    ? entries.reduce((total, item) => total + item.durationMs, 0) / entries.length
    : null;

  return {
    count: entries.length,
    latestMs: latestEntry?.durationMs ?? null,
    averageMs,
    latestLabel: latestEntry?.label ?? "",
    recordedAt: latestEntry?.recordedAt ?? "",
  };
});

const recentNavPerformanceEntries = computed(() => navPerformanceEntries.value.slice(-3).reverse());
const performanceFocusPath = ref("");

const loginPerformanceStatus = computed(() => resolvePerformanceStatus(loginPerformanceSummary.value.latestMs, "login"));
const navPerformanceStatus = computed(() => (
  resolvePerformanceStatus(navPerformanceSummary.value.averageMs ?? navPerformanceSummary.value.latestMs, "nav")
));
const baselinePathInsights = computed<BaselinePathInsight[]>(() => baselineDefinitions.map((definition) => {
  const entries = performanceEntries.value.filter((entry) => (
    entry.kind === definition.kind &&
    entry.sourcePath === definition.sourcePath &&
    entry.targetPath === definition.targetPath
  ));
  const latestEntry = entries[entries.length - 1];
  const averageMs = entries.length
    ? entries.reduce((total, item) => total + item.durationMs, 0) / entries.length
    : null;

  return {
    key: definition.key,
    label: definition.label,
    sourcePath: definition.sourcePath,
    targetPath: definition.targetPath,
    entries,
    count: entries.length,
    latestMs: latestEntry?.durationMs ?? null,
    averageMs,
    recordedAt: latestEntry?.recordedAt ?? "",
    status: resolvePerformanceStatus(averageMs ?? latestEntry?.durationMs, definition.statusKind),
    warmable: definition.warmable,
  };
}));
const baselineConclusion = computed<BaselineConclusion>(() => {
  const loginBaseline = baselinePathInsights.value.find((item) => item.key === "login-todo") ?? null;
  const observedBaselines = baselinePathInsights.value.filter((item) => item.count > 0);
  const warmableObservedBaselines = observedBaselines.filter((item) => item.warmable);

  const sortBySeverity = (items: BaselinePathInsight[]) => items
    .slice()
    .sort((left, right) => (
      (right.averageMs ?? right.latestMs ?? 0) - (left.averageMs ?? left.latestMs ?? 0)
    ));

  if (loginBaseline?.count && loginBaseline.status.shouldWarm) {
    return {
      title: "先守住登录首跳",
      note: `登录 -> Todo 当前约 ${formatDuration(loginBaseline.averageMs ?? loginBaseline.latestMs)}，首跳仍是最该先压的链路。`,
      status: loginBaseline.status,
      actionPath: null,
      actionLabel: "",
    };
  }

  const urgentBaseline = sortBySeverity(warmableObservedBaselines.filter((item) => item.status.shouldWarm))[0] ?? null;
  if (urgentBaseline) {
    return {
      title: `优先压 ${urgentBaseline.label}`,
      note: `这条高频链路当前约 ${formatDuration(urgentBaseline.averageMs ?? urgentBaseline.latestMs)}，已经到了建议优先预热的区间。`,
      status: urgentBaseline.status,
      actionPath: urgentBaseline.targetPath,
      actionLabel: "立即预热",
    };
  }

  const warningBaseline = sortBySeverity(warmableObservedBaselines.filter((item) => item.status.label === "偏慢"))[0] ?? null;
  if (warningBaseline) {
    return {
      title: `继续观察 ${warningBaseline.label}`,
      note: `这条链路当前约 ${formatDuration(warningBaseline.averageMs ?? warningBaseline.latestMs)}，还没到必须处理，但值得盯住。`,
      status: warningBaseline.status,
      actionPath: warningBaseline.targetPath,
      actionLabel: "手动预热",
    };
  }

  if (observedBaselines.length) {
    return {
      title: "当前高频基线稳定",
      note: `已记录 ${observedBaselines.length} 条关键链路，首跳和主导航目前都在可接受范围内。`,
      status: {
        label: "正常",
        tone: "success",
        note: "",
        shouldWarm: false,
      },
      actionPath: null,
      actionLabel: "",
    };
  }

  return {
    title: "先补一轮关键链路样本",
    note: "完成一次登录，再从 Todo 切到开发、客户、收费、更多，这里就能给出更准确的结论。",
    status: {
      label: "待观察",
      tone: "info",
      note: "",
      shouldWarm: false,
    },
    actionPath: null,
    actionLabel: "",
  };
});

const navPerformanceModuleInsights = computed<NavPerformanceInsight[]>(() => {
  if (!navPerformanceEntries.value.length) return [];

  const groups = new Map<string, {
    path: string;
    label: string;
    totalMs: number;
    count: number;
    latestMs: number;
  }>();

  for (const entry of navPerformanceEntries.value) {
    const current = groups.get(entry.targetPath);
    if (current) {
      current.totalMs += entry.durationMs;
      current.count += 1;
      current.latestMs = entry.durationMs;
      current.label = entry.targetLabel;
      continue;
    }

    groups.set(entry.targetPath, {
      path: entry.targetPath,
      label: entry.targetLabel,
      totalMs: entry.durationMs,
      count: 1,
      latestMs: entry.durationMs,
    });
  }

  return [...groups.values()]
    .map((item) => ({
      ...item,
      averageMs: item.totalMs / item.count,
      status: resolvePerformanceStatus(item.totalMs / item.count, "nav"),
    }))
    .sort((left, right) => right.averageMs - left.averageMs);
});

const slowNavInsight = computed(() => navPerformanceModuleInsights.value[0] ?? null);

const shouldWarmSlowNavInsight = computed(() => {
  if (!slowNavInsight.value) return false;
  return slowNavInsight.value.status.shouldWarm;
});

let stopPerformanceSubscription: (() => void) | null = null;

function resolveEntryIcon(key: string) {
  return entryIcons[key as keyof typeof entryIcons] || Files;
}

function warmMoreEntry(key: string) {
  prefetchMobileMoreEntry(key);
}

function formatDuration(value: number | null | undefined) {
  if (value == null) return "--";
  return `${Math.round(value)}ms`;
}

function formatRecordedAt(value: string) {
  if (!value) return "";
  const date = new Date(value);
  const hours = `${date.getHours()}`.padStart(2, "0");
  const minutes = `${date.getMinutes()}`.padStart(2, "0");
  const seconds = `${date.getSeconds()}`.padStart(2, "0");
  return `${hours}:${minutes}:${seconds}`;
}

function resolvePerformanceStatus(
  value: number | null | undefined,
  kind: "login" | "nav",
): PerformanceStatus {
  if (value == null) {
    return {
      label: "待观察",
      tone: "info",
      note: kind === "login" ? "等待下一次登录首跳记录。" : "等待下一次底部导航切页记录。",
      shouldWarm: false,
    };
  }

  const duration = value;
  const thresholds = kind === "login"
    ? { normal: 900, warm: 1400 }
    : { normal: 260, warm: 420 };

  if (duration <= thresholds.normal) {
    return {
      label: "正常",
      tone: "success",
      note: kind === "login" ? "当前登录首跳比较轻快。" : "当前切页节奏比较稳。",
      shouldWarm: false,
    };
  }

  if (duration <= thresholds.warm) {
    return {
      label: "偏慢",
      tone: "warning",
      note: kind === "login" ? "可以继续观察首跳耗时。" : "建议继续观察这条切页链路。",
      shouldWarm: false,
    };
  }

  return {
    label: "需要预热",
    tone: "danger",
    note: kind === "login" ? "首跳偏重，建议继续保留预热。" : "这条切页偏重，建议优先预热。",
    shouldWarm: true,
  };
}

function clearPerformance() {
  clearMobilePerformanceEntries();
  performanceFocusPath.value = "";
}

function warmPerformanceRoute(path: string) {
  prefetchMobileRoutePath(path);
  performanceFocusPath.value = path;
}

function warmSlowPerformanceRoute() {
  if (!slowNavInsight.value) return;
  warmPerformanceRoute(slowNavInsight.value.path);
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

onMounted(() => {
  performanceEntries.value = readMobilePerformanceEntries();
  stopPerformanceSubscription = subscribeMobilePerformanceEntries((entries) => {
    performanceEntries.value = entries;
  });
});

onBeforeUnmount(() => {
  stopPerformanceSubscription?.();
  stopPerformanceSubscription = null;
});

watch(slowNavInsight, (insight) => {
  if (!insight || !shouldWarmSlowNavInsight.value || performanceFocusPath.value === insight.path) return;
  warmPerformanceRoute(insight.path);
}, { immediate: true });
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

    <section class="mobile-more-section">
      <div class="mobile-more-head">
        <div>
          <div class="mobile-more-title">本次会话性能</div>
          <div class="mobile-more-copy">只记录手机端本次会话的真实耗时，关掉标签页后会清空。</div>
        </div>
        <el-button
          v-if="performanceEntries.length"
          size="small"
          class="mobile-row-secondary-button"
          @click="clearPerformance"
        >
          清空
        </el-button>
      </div>

      <template v-if="performanceEntries.length">
        <div class="mobile-performance-grid">
          <article class="mobile-performance-card">
            <div class="mobile-performance-card-head">
              <span>登录 -> Todo</span>
              <el-tag size="small" effect="plain" class="mobile-status-tag" :type="loginPerformanceStatus.tone">
                {{ loginPerformanceStatus.label }}
              </el-tag>
            </div>
            <strong>{{ formatDuration(loginPerformanceSummary.latestMs) }}</strong>
            <div class="mobile-performance-meta">
              <template v-if="loginPerformanceSummary.count">
                最快 {{ formatDuration(loginPerformanceSummary.fastestMs) }} · {{ loginPerformanceSummary.count }} 次
              </template>
              <template v-else>
                等待下一次登录记录
              </template>
            </div>
            <div v-if="loginPerformanceSummary.recordedAt" class="mobile-performance-time">
              {{ formatRecordedAt(loginPerformanceSummary.recordedAt) }}
            </div>
            <div class="mobile-performance-note">{{ loginPerformanceStatus.note }}</div>
          </article>

          <article class="mobile-performance-card">
            <div class="mobile-performance-card-head">
              <span>底部导航切页</span>
              <el-tag size="small" effect="plain" class="mobile-status-tag" :type="navPerformanceStatus.tone">
                {{ navPerformanceStatus.label }}
              </el-tag>
            </div>
            <strong>{{ formatDuration(navPerformanceSummary.latestMs) }}</strong>
            <div class="mobile-performance-meta">
              <template v-if="navPerformanceSummary.count">
                平均 {{ formatDuration(navPerformanceSummary.averageMs) }} · {{ navPerformanceSummary.count }} 次
              </template>
              <template v-else>
                等待下一次切页记录
              </template>
            </div>
            <div v-if="navPerformanceSummary.latestLabel" class="mobile-performance-time">
              最近 {{ navPerformanceSummary.latestLabel }}
            </div>
            <div class="mobile-performance-note">{{ navPerformanceStatus.note }}</div>
          </article>
        </div>

        <div class="mobile-performance-conclusion">
          <div class="mobile-performance-conclusion-main">
            <div class="mobile-performance-conclusion-head">
              <div class="mobile-performance-focus-kicker">基线结论</div>
              <el-tag size="small" effect="plain" class="mobile-status-tag" :type="baselineConclusion.status.tone">
                {{ baselineConclusion.status.label }}
              </el-tag>
            </div>
            <strong>{{ baselineConclusion.title }}</strong>
            <div class="mobile-performance-conclusion-copy">{{ baselineConclusion.note }}</div>
          </div>
          <el-button
            v-if="baselineConclusion.actionPath"
            size="small"
            :class="performanceFocusPath === baselineConclusion.actionPath ? 'mobile-row-secondary-button' : 'mobile-row-primary-button'"
            @click="warmPerformanceRoute(baselineConclusion.actionPath)"
          >
            {{ performanceFocusPath === baselineConclusion.actionPath ? "已预热" : baselineConclusion.actionLabel }}
          </el-button>
        </div>

        <div class="mobile-performance-baseline">
          <div class="mobile-performance-log-head">
            <div class="mobile-more-copy">关键链路基线</div>
            <el-tag size="small" effect="plain" class="mobile-count-tag">
              {{ baselinePathInsights.length }} 条
            </el-tag>
          </div>

          <div
            v-for="item in baselinePathInsights"
            :key="item.key"
            class="mobile-performance-baseline-item"
          >
            <div class="mobile-performance-baseline-main">
              <div class="mobile-performance-baseline-head">
                <strong>{{ item.label }}</strong>
                <el-tag size="small" effect="plain" class="mobile-status-tag" :type="item.status.tone">
                  {{ item.status.label }}
                </el-tag>
              </div>
              <div class="mobile-performance-baseline-copy">
                <template v-if="item.count">
                  平均 {{ formatDuration(item.averageMs) }} · 最近 {{ formatDuration(item.latestMs) }} · {{ item.count }} 次
                </template>
                <template v-else>
                  还没有这条链路的会话记录
                </template>
              </div>
              <div class="mobile-performance-baseline-copy">{{ item.status.note }}</div>
              <div v-if="item.recordedAt" class="mobile-performance-time">
                最近记录 {{ formatRecordedAt(item.recordedAt) }}
              </div>
            </div>

            <el-button
              v-if="item.warmable"
              size="small"
              :class="performanceFocusPath === item.targetPath ? 'mobile-row-secondary-button' : 'mobile-row-primary-button'"
              @click="warmPerformanceRoute(item.targetPath)"
            >
              {{ performanceFocusPath === item.targetPath ? "已预热" : item.status.shouldWarm ? "优先预热" : "预热" }}
            </el-button>
          </div>
        </div>

        <div v-if="recentNavPerformanceEntries.length" class="mobile-performance-log">
          <div v-if="slowNavInsight" class="mobile-performance-focus">
            <div class="mobile-performance-focus-main">
              <div class="mobile-performance-focus-head">
                <div class="mobile-performance-focus-kicker">当前最慢模块</div>
                <el-tag
                  size="small"
                  effect="plain"
                  class="mobile-status-tag"
                  :type="slowNavInsight.status.tone"
                >
                  {{ slowNavInsight.status.label }}
                </el-tag>
              </div>
              <strong>{{ slowNavInsight.label }}</strong>
              <div class="mobile-performance-focus-copy">
                平均 {{ formatDuration(slowNavInsight.averageMs) }} · 最近 {{ formatDuration(slowNavInsight.latestMs) }} · {{ slowNavInsight.count }} 次
              </div>
              <div class="mobile-performance-focus-copy">
                {{ slowNavInsight.status.note }}
              </div>
            </div>
            <el-button
              size="small"
              :class="performanceFocusPath === slowNavInsight.path ? 'mobile-row-secondary-button' : 'mobile-row-primary-button'"
              @click="warmSlowPerformanceRoute"
            >
              {{
                performanceFocusPath === slowNavInsight.path
                  ? "已预热"
                  : slowNavInsight.status.shouldWarm
                    ? "立即预热"
                    : "手动预热"
              }}
            </el-button>
          </div>

          <div v-if="navPerformanceModuleInsights.length" class="mobile-performance-distribution">
            <div class="mobile-performance-log-head">
              <div class="mobile-more-copy">按模块分布</div>
              <el-tag size="small" effect="plain" class="mobile-count-tag">
                {{ navPerformanceModuleInsights.length }} 个
              </el-tag>
            </div>

            <div
              v-for="item in navPerformanceModuleInsights"
              :key="item.path"
              class="mobile-performance-distribution-item"
            >
              <div class="mobile-performance-distribution-main">
                <div class="mobile-performance-distribution-head">
                  <strong>{{ item.label }}</strong>
                  <el-tag size="small" effect="plain" class="mobile-status-tag" :type="item.status.tone">
                    {{ item.status.label }}
                  </el-tag>
                </div>
                <div class="mobile-performance-distribution-copy">
                  平均 {{ formatDuration(item.averageMs) }} · 最近 {{ formatDuration(item.latestMs) }} · {{ item.count }} 次
                </div>
                <div class="mobile-performance-distribution-copy">{{ item.status.note }}</div>
              </div>
              <el-button
                size="small"
                :class="performanceFocusPath === item.path ? 'mobile-row-secondary-button' : 'mobile-row-primary-button'"
                @click="warmPerformanceRoute(item.path)"
              >
                {{ performanceFocusPath === item.path ? "已预热" : item.status.shouldWarm ? "优先预热" : "预热" }}
              </el-button>
            </div>
          </div>

          <div class="mobile-performance-log-head">
            <div class="mobile-more-copy">最近切页</div>
            <el-tag size="small" effect="plain" class="mobile-count-tag">
              {{ recentNavPerformanceEntries.length }} 条
            </el-tag>
          </div>
          <div
            v-for="entry in recentNavPerformanceEntries"
            :key="entry.id"
            class="mobile-performance-log-item"
          >
            <div class="mobile-performance-log-main">
              <strong>{{ entry.label }}</strong>
              <span>{{ formatRecordedAt(entry.recordedAt) }}</span>
            </div>
            <div class="mobile-performance-log-value">{{ formatDuration(entry.durationMs) }}</div>
          </div>
        </div>
      </template>

      <div v-else class="mobile-empty-block">
        <div class="mobile-empty-kicker">Session</div>
        <div class="mobile-empty-title">还没有手机端性能记录</div>
        <div class="mobile-empty-copy">登录一次或用底部导航切页后，这里会显示真实耗时。</div>
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
        @focus="warmMoreEntry(entry.key)"
        @pointerenter="warmMoreEntry(entry.key)"
        @touchstart.passive="warmMoreEntry(entry.key)"
        @click="router.push(entry.path)"
      >
        <div class="mobile-more-entry-main">
          <component :is="resolveEntryIcon(entry.key)" class="mobile-more-entry-icon" />
          <div class="mobile-more-entry-copy-block">
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
          <div class="mobile-more-entry-copy-block">
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

.mobile-more-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.mobile-more-copy {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--app-text-muted);
}

.mobile-performance-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 12px;
}

.mobile-performance-card {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 12px;
  border: 1px solid var(--app-border-soft);
  background: var(--app-bg-soft);
}

.mobile-performance-card-head,
.mobile-performance-focus-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.mobile-performance-card span {
  font-size: 11px;
  color: var(--app-text-muted);
}

.mobile-performance-card strong {
  font-size: 20px;
  line-height: 1;
  color: var(--app-text-primary);
}

.mobile-performance-meta,
.mobile-performance-time {
  font-size: 11px;
  color: var(--app-text-muted);
}

.mobile-performance-note {
  font-size: 11px;
  color: var(--app-text-secondary);
}

.mobile-performance-conclusion {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
  padding: 12px;
  border: 1px solid var(--app-border-soft);
  background: color-mix(in srgb, var(--app-bg-soft) 88%, white 12%);
}

.mobile-performance-conclusion-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.mobile-performance-conclusion-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.mobile-performance-conclusion-main strong {
  font-size: 14px;
  color: var(--app-text-primary);
}

.mobile-performance-conclusion-copy {
  font-size: 11px;
  color: var(--app-text-muted);
}

.mobile-performance-baseline {
  margin-top: 12px;
  border-top: 1px solid var(--app-border-soft);
  border-bottom: 1px solid var(--app-border-soft);
}

.mobile-performance-baseline-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--app-border-soft);
}

.mobile-performance-baseline-item:last-child {
  border-bottom: none;
}

.mobile-performance-baseline-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.mobile-performance-baseline-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.mobile-performance-baseline-head strong {
  font-size: 13px;
  color: var(--app-text-primary);
}

.mobile-performance-baseline-copy {
  font-size: 11px;
  color: var(--app-text-muted);
}

.mobile-performance-log {
  margin-top: 12px;
  border-top: 1px solid var(--app-border-soft);
}

.mobile-performance-focus {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--app-border-soft);
}

.mobile-performance-focus-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.mobile-performance-focus-kicker {
  font-size: 11px;
  color: var(--app-accent-strong);
}

.mobile-performance-focus-main strong {
  font-size: 14px;
  color: var(--app-text-primary);
}

.mobile-performance-focus-copy {
  font-size: 11px;
  color: var(--app-text-muted);
}

.mobile-performance-distribution {
  border-bottom: 1px solid var(--app-border-soft);
}

.mobile-performance-distribution-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--app-border-soft);
}

.mobile-performance-distribution-item:last-child {
  border-bottom: none;
}

.mobile-performance-distribution-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.mobile-performance-distribution-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.mobile-performance-distribution-head strong {
  font-size: 13px;
  color: var(--app-text-primary);
}

.mobile-performance-distribution-copy {
  font-size: 11px;
  color: var(--app-text-muted);
}

.mobile-performance-log-head,
.mobile-performance-log-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.mobile-performance-log-head {
  padding-top: 12px;
}

.mobile-performance-log-item {
  padding: 12px 0;
  border-bottom: 1px solid var(--app-border-soft);
}

.mobile-performance-log-item:last-child {
  padding-bottom: 0;
  border-bottom: none;
}

.mobile-performance-log-main {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.mobile-performance-log-main strong {
  font-size: 13px;
  color: var(--app-text-primary);
}

.mobile-performance-log-main span,
.mobile-performance-log-value {
  font-size: 11px;
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

.mobile-more-entry-copy-block {
  min-width: 0;
  flex: 1;
}

.mobile-more-entry:first-of-type {
  margin-top: 10px;
}

.mobile-more-entry-icon {
  width: 18px;
  height: 18px;
  display: block;
  margin-top: 2px;
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

@media (max-width: 480px) {
  .mobile-profile-signal-grid,
  .mobile-performance-grid {
    grid-template-columns: 1fr;
  }

  .mobile-performance-focus {
    align-items: flex-start;
    flex-direction: column;
  }

  .mobile-performance-card-head,
  .mobile-performance-conclusion-head,
  .mobile-performance-baseline-head,
  .mobile-performance-focus-head,
  .mobile-performance-distribution-head {
    width: 100%;
  }

  .mobile-performance-conclusion,
  .mobile-performance-baseline-item,
  .mobile-performance-distribution-item {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
