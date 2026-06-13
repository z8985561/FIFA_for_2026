<script setup lang="ts">
import DataCompletenessBadge from '@/components/common/DataCompletenessBadge.vue'
import type { DataQualityRow } from '@/types/api'

const props = defineProps<{
  quality: Readonly<DataQualityRow> | null
}>()

const capabilityItems: Array<{
  key: keyof Pick<
    DataQualityRow,
    | 'has_fixture'
    | 'has_prediction'
    | 'has_scoreline_model'
    | 'has_score_odds'
    | 'has_market_odds'
    | 'has_lineup_adjustment'
  >
  label: string
}> = [
  { key: 'has_fixture', label: '赛程' },
  { key: 'has_prediction', label: '胜平负预测' },
  { key: 'has_scoreline_model', label: '比分模型' },
  { key: 'has_score_odds', label: '比分赔率' },
  { key: 'has_market_odds', label: '市场赔率' },
  { key: 'has_lineup_adjustment', label: '阵容修正' },
]

const missingLabels: Record<string, string> = {
  missing_prediction: '胜平负预测',
  missing_scoreline_model: '比分模型',
  missing_score_odds: '比分赔率',
  missing_market_odds: '市场赔率',
  missing_lineup_adjustment: '阵容修正',
  missing_snapshot_time: '快照时间',
}

function formatTime(value?: string | null) {
  if (!value) {
    return '暂无'
  }
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function missingText(items: readonly string[]) {
  if (!items.length) {
    return '核心数据已接入'
  }
  return items.map((item) => missingLabels[item] ?? item).join('、')
}
</script>

<template>
  <section class="section-card completeness-card">
    <div class="section-title">
      <h2>数据完整度</h2>
      <DataCompletenessBadge
        :level="quality?.completeness_level"
        :score="quality?.completeness_score"
        :missing-items="quality?.missing_items ?? []"
      />
    </div>

    <p class="completeness-note">
      数据完整度表示当前比赛接入的数据是否齐全，不等于模型预测准确率。
    </p>

    <div v-if="quality" class="completeness-grid">
      <div class="capability-list">
        <article
          v-for="item in capabilityItems"
          :key="item.key"
          class="capability-item"
          :class="{ ready: quality[item.key] }"
        >
          <strong>{{ item.label }}</strong>
          <span>{{ quality[item.key] ? '已接入' : '暂未接入' }}</span>
        </article>
      </div>

      <div class="side-column">
        <div class="side-card">
          <span>比分赔率快照</span>
          <strong>{{ formatTime(quality.latest_score_odds_fetched_at) }}</strong>
        </div>
        <div class="side-card">
          <span>市场赔率快照</span>
          <strong>{{ formatTime(quality.latest_market_fetched_at) }}</strong>
        </div>
        <div class="side-card">
          <span>缺失项</span>
          <p>{{ missingText(quality.missing_items) }}</p>
        </div>
      </div>
    </div>

    <ElSkeleton v-else :rows="4" animated />
  </section>
</template>

<style scoped>
.completeness-card {
  display: grid;
  gap: 16px;
}

.completeness-note {
  margin: 0;
  color: var(--color-muted);
  line-height: 1.7;
}

.completeness-grid {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 18px;
}

.capability-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.capability-item,
.side-card {
  padding: 16px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
  background: rgba(18, 35, 64, 0.5);
}

.capability-item {
  display: grid;
  gap: 6px;
}

.capability-item span,
.side-card span,
.side-card p {
  color: var(--color-muted);
}

.capability-item.ready {
  border-color: rgba(45, 117, 109, 0.28);
  background: rgba(45, 117, 109, 0.08);
}

.side-column {
  display: grid;
  gap: 12px;
}

.side-card {
  display: grid;
  gap: 6px;
}

.side-card strong {
  font-size: 16px;
}

.side-card p {
  margin: 0;
  line-height: 1.7;
}

@media (max-width: 900px) {
  .completeness-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .capability-list {
    grid-template-columns: 1fr;
  }
}
</style>
