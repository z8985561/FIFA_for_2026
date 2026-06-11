<script setup lang="ts">
import type { MatchSummary } from '@/types/api'

defineProps<{
  matches: readonly MatchSummary[]
  activeMatchNo: number
  loading?: boolean
}>()

const emit = defineEmits<{
  select: [matchNo: number]
}>()

function percent(value?: number | null) {
  return value == null ? '暂无' : `${(value * 100).toFixed(1)}%`
}
</script>

<template>
  <section class="switcher">
    <div class="switcher-head">
      <div>
        <span class="eyebrow">Quick Switch</span>
        <h2>前四场快速切换</h2>
      </div>
      <span>{{ loading ? '加载中...' : `${matches.length} 场` }}</span>
    </div>

    <div class="switcher-grid">
      <button
        v-for="match in matches"
        :key="match.match_no"
        type="button"
        class="switcher-item"
        :class="{ active: match.match_no === activeMatchNo }"
        @click="emit('select', match.match_no)"
      >
        <span>第 {{ match.match_no }} 场 · {{ match.group_name }}</span>
        <strong>{{ match.home_team_zh }} vs {{ match.away_team_zh }}</strong>
        <small>
          Top 比分 {{ match.top_scoreline ?? '暂无' }}
          · {{ percent(match.top_scoreline_probability) }}
        </small>
      </button>
    </div>
  </section>
</template>

<style scoped>
.switcher {
  padding: 22px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-xl);
  background: var(--surface-glass);
  box-shadow: var(--shadow-soft);
}

.switcher-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 18px;
}

.switcher-head h2 {
  margin: 6px 0 0;
}

.switcher-head > span {
  color: var(--color-muted);
}

.switcher-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.switcher-item {
  display: grid;
  gap: 8px;
  width: 100%;
  padding: 16px;
  text-align: left;
  color: var(--color-ink);
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.58);
  cursor: pointer;
  transition:
    transform 160ms ease,
    border-color 160ms ease,
    background 160ms ease;
}

.switcher-item:hover {
  transform: translateY(-2px);
  border-color: rgba(200, 88, 72, 0.42);
}

.switcher-item.active {
  color: #f8efe0;
  border-color: rgba(22, 45, 54, 0.85);
  background: linear-gradient(145deg, #17282d, #24454b);
}

.switcher-item span,
.switcher-item small {
  color: var(--color-muted);
}

.switcher-item.active span,
.switcher-item.active small {
  color: rgba(248, 239, 224, 0.72);
}

.switcher-item strong {
  font-size: 18px;
}

@media (max-width: 1180px) {
  .switcher-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .switcher-grid {
    grid-template-columns: 1fr;
  }
}
</style>
