<script setup lang="ts">
import type { MatchSummary } from '@/types/api'

const props = defineProps<{
  matches: MatchSummary[]
}>()

function outcomeLabel(value?: string | null) {
  if (value === 'home_win') {
    return '主胜'
  }
  if (value === 'draw') {
    return '平局'
  }
  if (value === 'away_win') {
    return '客胜'
  }
  return '暂无'
}

function actualOutcome(match: MatchSummary) {
  if (match.actual_home_score == null || match.actual_away_score == null) {
    return null
  }
  if (match.actual_home_score > match.actual_away_score) {
    return 'home_win'
  }
  if (match.actual_home_score < match.actual_away_score) {
    return 'away_win'
  }
  return 'draw'
}

function actualScoreline(match: MatchSummary) {
  if (match.actual_home_score == null || match.actual_away_score == null) {
    return '待赛'
  }
  return `${match.actual_home_score}-${match.actual_away_score}`
}

function outcomeVerdict(match: MatchSummary) {
  const actual = actualOutcome(match)
  if (!actual || !match.predicted_outcome) {
    return '待赛果'
  }
  return actual === match.predicted_outcome ? '方向命中' : '方向偏离'
}

function scoreVerdict(match: MatchSummary) {
  if (!match.top_scoreline || actualScoreline(match) === '待赛') {
    return '待赛果'
  }
  return match.top_scoreline === actualScoreline(match) ? '比分命中' : '比分偏离'
}
</script>

<template>
  <div class="review-grid">
    <article v-for="match in props.matches" :key="match.match_no" class="review-card">
      <div class="review-head">
        <div>
          <span class="review-kicker">第 {{ match.match_no }} 场 · {{ match.group_name }}</span>
          <h3>{{ match.home_team_zh }} vs {{ match.away_team_zh }}</h3>
        </div>
        <RouterLink :to="`/matches/${match.match_no}`" class="review-link">查看复盘</RouterLink>
      </div>

      <div class="review-score">
        <strong>{{ actualScoreline(match) }}</strong>
        <span>{{ match.result_source_name ?? '暂无来源' }}</span>
      </div>

      <div class="review-metrics">
        <div>
          <span>模型方向</span>
          <strong>{{ outcomeLabel(match.predicted_outcome) }}</strong>
          <small>{{ outcomeVerdict(match) }}</small>
        </div>
        <div>
          <span>模型 Top 比分</span>
          <strong>{{ match.top_scoreline ?? '暂无' }}</strong>
          <small>{{ scoreVerdict(match) }}</small>
        </div>
      </div>
    </article>
  </div>
</template>

<style scoped>
.review-grid {
  display: grid;
  gap: 16px;
}

.review-card {
  display: grid;
  gap: 16px;
  padding: 20px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-xl);
  background:
    linear-gradient(155deg, rgba(255, 255, 255, 0.92), rgba(242, 236, 226, 0.82)),
    radial-gradient(circle at top right, rgba(34, 110, 84, 0.1), transparent 32%);
}

.review-head {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 16px;
}

.review-kicker {
  color: var(--color-muted);
  font-size: 13px;
}

.review-head h3 {
  margin: 6px 0 0;
  font-size: 22px;
}

.review-link {
  color: var(--color-accent);
  text-decoration: none;
  font-weight: 700;
}

.review-score {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 16px;
}

.review-score strong {
  font-size: 34px;
  line-height: 1;
}

.review-score span {
  color: var(--color-muted);
  font-size: 13px;
}

.review-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.review-metrics div {
  display: grid;
  gap: 6px;
  padding: 14px;
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.62);
}

.review-metrics span,
.review-metrics small {
  color: var(--color-muted);
  font-size: 13px;
}

.review-metrics strong {
  font-size: 22px;
}

@media (max-width: 900px) {
  .review-head,
  .review-score {
    grid-template-columns: 1fr;
    display: grid;
  }

  .review-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
