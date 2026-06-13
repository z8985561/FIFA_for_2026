<script setup lang="ts">
import { computed } from 'vue'

import DataCompletenessBadge from '@/components/common/DataCompletenessBadge.vue'
import type { DataQualityRow, MatchSummary } from '@/types/api'

const props = defineProps<{
  rows: readonly DataQualityRow[]
  focusMatches: readonly MatchSummary[]
  loading?: boolean
  error?: string | null
}>()

const summaryCards = computed(() => {
  const rows = props.rows
  return [
    {
      label: 'High',
      value: rows.filter((row) => row.completeness_level === 'High').length,
      tone: 'high',
    },
    {
      label: 'Medium',
      value: rows.filter((row) => row.completeness_level === 'Medium').length,
      tone: 'medium',
    },
    {
      label: 'Low',
      value: rows.filter((row) => row.completeness_level === 'Low').length,
      tone: 'low',
    },
  ]
})

const focusRows = computed(() => {
  return props.focusMatches.map((match) => {
    const quality =
      props.rows.find((row) => row.match_no === match.match_no) ?? null
    return { match, quality }
  })
})

const coreChecks = [
  { key: 'has_prediction', label: '胜平负预测' },
  { key: 'has_scoreline_model', label: '比分模型' },
  { key: 'has_score_odds', label: '比分赔率' },
  { key: 'has_market_odds', label: '市场赔率' },
] as const
</script>

<template>
  <section class="section-card completeness-summary">
    <div class="section-title">
      <h2>数据完整度摘要</h2>
      <span>展示覆盖情况，不代表模型准确率</span>
    </div>

    <ElAlert
      v-if="error"
      :title="error"
      type="warning"
      show-icon
      :closable="false"
    />

    <ElSkeleton v-else-if="loading && !rows.length" :rows="4" animated />

    <template v-else>
      <div class="summary-grid">
        <article
          v-for="card in summaryCards"
          :key="card.label"
          class="summary-card"
          :class="`summary-card--${card.tone}`"
        >
          <span>{{ card.label }}</span>
          <strong>{{ card.value }}</strong>
        </article>
      </div>

      <div class="focus-list">
        <article
          v-for="item in focusRows"
          :key="item.match.match_no"
          class="focus-card"
        >
          <div class="focus-header">
            <div>
              <span class="focus-meta">第 {{ item.match.match_no }} 场</span>
              <h3>
                {{ item.match.home_team_zh }} vs {{ item.match.away_team_zh }}
              </h3>
            </div>
            <DataCompletenessBadge
              :level="item.quality?.completeness_level"
              :score="item.quality?.completeness_score"
              :missing-items="item.quality?.missing_items ?? []"
            />
          </div>

          <div class="check-grid">
            <div
              v-for="check in coreChecks"
              :key="check.key"
              class="check-item"
              :class="{ ready: item.quality?.[check.key] }"
            >
              <span>{{ check.label }}</span>
              <strong>{{ item.quality?.[check.key] ? '已接入' : '暂未接入' }}</strong>
            </div>
          </div>
        </article>
      </div>
    </template>
  </section>
</template>

<style scoped>
.completeness-summary {
  display: grid;
  gap: 16px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.summary-card,
.focus-card {
  padding: 18px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
  background: rgba(18, 35, 64, 0.5);
}

.summary-card {
  display: grid;
  gap: 8px;
}

.summary-card span {
  color: var(--color-muted);
}

.summary-card strong {
  font-size: 28px;
}

.summary-card--high {
  border-color: rgba(45, 117, 109, 0.25);
}

.summary-card--medium {
  border-color: rgba(205, 145, 58, 0.25);
}

.summary-card--low {
  border-color: rgba(184, 179, 169, 0.32);
}

.focus-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.focus-card {
  display: grid;
  gap: 14px;
}

.focus-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.focus-meta {
  color: var(--color-muted);
  font-size: 13px;
}

.focus-header h3 {
  margin: 6px 0 0;
  font-size: 18px;
}

.check-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.check-item {
  display: grid;
  gap: 4px;
  padding: 12px;
  border-radius: var(--radius-md);
  background: rgba(184, 179, 169, 0.1);
}

.check-item span {
  color: var(--color-muted);
}

.check-item.ready {
  background: rgba(45, 117, 109, 0.1);
}

@media (max-width: 900px) {
  .summary-grid,
  .focus-list,
  .check-grid {
    grid-template-columns: 1fr;
  }

  .focus-header {
    flex-direction: column;
  }
}
</style>
