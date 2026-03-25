<script setup lang="ts">
const overviewCards = [
  { label: "本月应收", value: "128,000", tone: "accent", note: "含续费与未到期应收。" },
  { label: "本月实收", value: "96,000", tone: "neutral", note: "到账已确认并完成核对。" },
  { label: "逾期应收", value: "32,000", tone: "danger", note: "需要继续催收和跟进。" },
];

const attentionRows = [
  { title: "应收回款差额", value: "32,000", note: "本月应收与实收之间的差额，需要继续追踪。" },
  { title: "逾期客户数", value: "11", note: "先处理账期最长和金额最高的客户。" },
  { title: "本周重点", value: "催收 / 核对 / 续费", note: "先把逾期回款收口，再看成本录入。" },
];

const roadmapRows = [
  { title: "老板先看什么", copy: "先守住回款、逾期和催收节奏，再决定是否需要补成本明细。" },
  { title: "下一步上线", copy: "成本录入、客户利润明细、月度毛利对比会在下一阶段并入这里。" },
  { title: "当前阶段定位", copy: "这页现在负责老板快速判断压力，而不是承载完整财务报表。" },
];
</script>

<template>
  <section class="cost-view-page">
    <section class="cost-hero">
      <div class="cost-hero-copy">
        <div class="cost-eyebrow">老板视图</div>
        <div class="cost-title">成本与老板视图</div>
        <div class="cost-copy">先看回款压力和逾期风险，成本录入与利润明细下一阶段并入。</div>
      </div>
      <el-tag type="warning" effect="plain">Phase 6</el-tag>
    </section>

    <section class="cost-card-grid">
      <article
        v-for="item in overviewCards"
        :key="item.label"
        class="cost-card"
        :class="item.tone"
      >
        <div class="cost-card-label">{{ item.label }}</div>
        <div class="cost-card-value">{{ item.value }}</div>
        <div class="cost-card-note">{{ item.note }}</div>
      </article>
    </section>

    <section class="cost-section">
      <div class="cost-section-head">
        <div>
          <div class="cost-section-title">当前需要盯住的信号</div>
          <div class="cost-section-copy">这不是完整成本报表，而是老板优先级面板。</div>
        </div>
      </div>
      <div class="cost-attention-grid">
        <article v-for="item in attentionRows" :key="item.title" class="cost-attention-card">
          <div class="cost-attention-title">{{ item.title }}</div>
          <div class="cost-attention-value">{{ item.value }}</div>
          <div class="cost-attention-copy">{{ item.note }}</div>
        </article>
      </div>
    </section>

    <section class="cost-section cost-roadmap-section">
      <div class="cost-roadmap-figure" aria-hidden="true">
        <div class="cost-roadmap-plane"></div>
        <div class="cost-roadmap-circle"></div>
      </div>
      <div class="cost-roadmap-copy">
        <div class="cost-section-title">接下来会补齐什么</div>
        <div class="cost-section-copy">先把这页做成可判断的经营概览，再逐步补完整成本链路。</div>
        <div class="cost-roadmap-list">
          <article v-for="item in roadmapRows" :key="item.title" class="cost-roadmap-row">
            <div class="cost-roadmap-title">{{ item.title }}</div>
            <div class="cost-roadmap-text">{{ item.copy }}</div>
          </article>
        </div>
      </div>
    </section>
  </section>
</template>

<style scoped>
.cost-view-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.cost-hero,
.cost-section {
  border: 1px solid var(--app-border-soft);
  background: rgba(255, 255, 255, 0.92);
  box-shadow: var(--app-shadow-soft);
  padding: 16px;
}

.cost-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.cost-hero-copy {
  min-width: 0;
  flex: 1;
}

.cost-eyebrow {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--app-text-muted);
}

.cost-title,
.cost-section-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.cost-copy,
.cost-section-copy,
.cost-card-note,
.cost-attention-copy,
.cost-roadmap-text {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--app-text-muted);
}

.cost-card-grid,
.cost-attention-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.cost-card,
.cost-attention-card {
  border: 1px solid var(--app-border-soft);
  background: var(--app-surface);
  padding: 14px;
}

.cost-card.accent {
  background: linear-gradient(135deg, rgba(77, 128, 150, 0.14), rgba(255, 255, 255, 0.96));
}

.cost-card.danger {
  background: linear-gradient(135deg, rgba(187, 77, 77, 0.12), rgba(255, 255, 255, 0.96));
}

.cost-card-label,
.cost-attention-title,
.cost-roadmap-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--app-text-secondary);
}

.cost-card-value,
.cost-attention-value {
  margin-top: 8px;
  font-size: 22px;
  font-weight: 700;
  color: var(--app-text-primary);
}

.cost-roadmap-section {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  gap: 18px;
  align-items: center;
}

.cost-roadmap-figure {
  position: relative;
  min-height: 180px;
  border: 1px solid var(--app-border-soft);
  background:
    radial-gradient(circle at 30% 30%, rgba(77, 128, 150, 0.12), transparent 48%),
    linear-gradient(180deg, rgba(245, 248, 248, 0.9), rgba(255, 255, 255, 0.98));
  overflow: hidden;
}

.cost-roadmap-plane,
.cost-roadmap-circle {
  position: absolute;
  border: 8px solid rgba(49, 92, 115, 0.18);
}

.cost-roadmap-plane {
  inset: 24px 22px auto;
  height: 78px;
}

.cost-roadmap-circle {
  width: 88px;
  height: 88px;
  right: 18px;
  bottom: 18px;
  border-radius: 999px;
}

.cost-roadmap-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.cost-roadmap-row {
  padding-top: 10px;
  border-top: 1px solid var(--app-border-soft);
}

.cost-roadmap-row:first-child {
  padding-top: 0;
  border-top: none;
}

@media (max-width: 768px) {
  .cost-hero {
    flex-direction: column;
  }

  .cost-card-grid,
  .cost-attention-grid,
  .cost-roadmap-section {
    grid-template-columns: 1fr;
  }

  .cost-roadmap-figure {
    min-height: 140px;
  }
}
</style>
