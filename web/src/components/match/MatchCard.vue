<script setup lang="ts">
import type { MatchSummary } from '@/types/api'

defineProps<{
  match: MatchSummary
}>()

function percent(value?: number | null) {
  return value == null ? '暂无' : `${(value * 100).toFixed(1)}%`
}
</script>

<template>
  <RouterLink :to="`/matches/${match.match_no}`" class="match-card">
    <div class="match-meta">
      <span>第 {{ match.match_no }} 场</span>
      <span>{{ match.group_name }}</span>
    </div>
    <h3>{{ match.home_team_zh }} vs {{ match.away_team_zh }}</h3>
    <p class="venue">{{ match.date_bj }} {{ match.time_bj }} · {{ match.venue_city }}</p>
    <div class="prob-grid">
      <span>主胜 {{ percent(match.home_win_probability) }}</span>
      <span>平局 {{ percent(match.draw_probability) }}</span>
      <span>客胜 {{ percent(match.away_win_probability) }}</span>
    </div>
    <footer>
      <span>Top 比分：{{ match.top_scoreline ?? '暂无' }}</span>
      <span>{{ percent(match.top_scoreline_probability) }}</span>
    </footer>
  </RouterLink>
</template>

<style scoped>
.match-card {
  display: grid;
  gap: 14px;
  padding: 22px;
  min-height: 220px;
  color: inherit;
  text-decoration: none;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-xl);
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.9), rgba(245, 238, 223, 0.78)),
    radial-gradient(circle at top right, rgba(200, 88, 72, 0.12), transparent 32%);
  box-shadow: var(--shadow-soft);
  transition:
    transform 180ms ease,
    border-color 180ms ease;
}

.match-card:hover {
  transform: translateY(-3px);
  border-color: rgba(200, 88, 72, 0.45);
}

.match-meta,
.prob-grid,
footer {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  color: var(--color-muted);
  font-size: 13px;
}

h3 {
  margin: 0;
  font-size: 24px;
}

.venue {
  margin: 0;
  color: var(--color-muted);
}

.prob-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
}

footer {
  padding-top: 12px;
  border-top: 1px solid var(--color-line);
  color: var(--color-ink);
  font-weight: 700;
}
</style>
