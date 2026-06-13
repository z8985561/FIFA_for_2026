<script setup lang="ts">
import type { MatchReviewRow } from '@/types/api'

const props = defineProps<{
  reviews: readonly MatchReviewRow[]
}>()

function bucketLabel(bucket: string): string {
  const map: Record<string, string> = {
    exact_hit: '精确命中',
    outcome_hit_only: '方向命中',
    upset_miss: '冷门偏差',
    outcome_miss: '方向偏离',
    scoreline_hit: '比分命中',
    outcome_hit_scoreline_miss: '方向对/比分错',
  }
  return map[bucket] || bucket
}

function bucketType(bucket: string): 'success' | 'danger' | 'warning' | 'info' {
  if (bucket === 'exact_hit' || bucket === 'scoreline_hit') return 'success'
  if (bucket === 'upset_miss' || bucket === 'outcome_miss') return 'danger'
  if (bucket === 'outcome_hit_only' || bucket === 'outcome_hit_scoreline_miss') return 'warning'
  return 'info'
}
</script>

<template>
  <section v-if="props.reviews.length" class="section-card">
    <div class="section-title">
      <h2>赛后深度复盘</h2>
      <span>预期 vs 实际进球分析</span>
    </div>

    <div class="review-insight-grid">
      <article
        v-for="review in props.reviews"
        :key="review.match_no"
        class="insight-card"
      >
        <div class="insight-head">
          <div>
            <span class="insight-kicker">
              第 {{ review.match_no }} 场 · {{ review.group_name }}
            </span>
            <h3>{{ review.home_team_zh }} vs {{ review.away_team_zh }}</h3>
          </div>
          <ElTag :type="bucketType(review.review_bucket)" size="small">
            {{ bucketLabel(review.review_bucket) }}
          </ElTag>
        </div>

        <div class="insight-score">
          <strong>{{ review.actual_scoreline || '待赛' }}</strong>
        </div>

        <div class="insight-metrics">
          <div class="metric">
            <span>模型预期总进球</span>
            <strong>{{ review.expected_total_goals?.toFixed(2) ?? '暂无' }}</strong>
          </div>
          <div class="metric">
            <span>实际总进球</span>
            <strong>{{ review.actual_total_goals ?? '暂无' }}</strong>
          </div>
          <div class="metric">
            <span>误差</span>
            <strong :class="{
              'text-green': review.total_goals_error != null && Math.abs(review.total_goals_error) < 0.5,
              'text-red': review.total_goals_error != null && Math.abs(review.total_goals_error) >= 1.5,
            }">
              {{ review.total_goals_error != null
                ? (review.total_goals_error >= 0 ? '+' : '') + review.total_goals_error.toFixed(2)
                : '暂无' }}
            </strong>
          </div>
        </div>

        <div class="insight-footer">
          <span>
            {{ review.outcome_hit ? '✓ 方向命中' : '✗ 方向偏离' }}
          </span>
          <span>
            {{ review.scoreline_hit ? '✓ 比分命中' : '✗ 比分偏离' }}
          </span>
          <span v-if="review.actual_outcome_probability != null">
            真实结果置信度 {{ (review.actual_outcome_probability * 100).toFixed(0) }}%
          </span>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.review-insight-grid {
  display: grid;
  gap: 16px;
}

.insight-card {
  display: grid;
  gap: 14px;
  padding: 20px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
  background: rgba(18, 35, 64, 0.5);
}

.insight-head {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 12px;
}

.insight-kicker {
  color: var(--color-muted);
  font-size: 13px;
}

.insight-head h3 {
  margin: 4px 0 0;
  font-size: 20px;
}

.insight-score strong {
  font-size: 32px;
  line-height: 1;
}

.insight-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.metric {
  display: grid;
  gap: 4px;
  padding: 12px;
  border-radius: var(--radius-md);
  background: rgba(0, 0, 0, 0.02);
}

.metric span {
  color: var(--color-muted);
  font-size: 12px;
}

.metric strong {
  font-size: 20px;
}

.insight-footer {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 13px;
  color: var(--color-muted);
}

.text-green {
  color: #16a34a;
}

.text-red {
  color: #dc2626;
}

@media (max-width: 900px) {
  .insight-metrics {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
