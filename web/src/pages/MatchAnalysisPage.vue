<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import StatCard from '@/components/common/StatCard.vue'
import FactorWaterfall from '@/components/match/FactorWaterfall.vue'
import MatchCompletenessCard from '@/components/match/MatchCompletenessCard.vue'
import MatchSwitcher from '@/components/match/MatchSwitcher.vue'
import ScorelineProbabilityChart from '@/components/match/ScorelineProbabilityChart.vue'
import ScorelineTable from '@/components/match/ScorelineTable.vue'
import { useAsyncState } from '@/composables/useAsyncState'
import { dashboardApi } from '@/services/api'
import { useMatchStore } from '@/stores/match'
import type { DataQualityRow, MatchDetail, ScorelineRow } from '@/types/api'

const route = useRoute()
const router = useRouter()
const matchStore = useMatchStore()
const detail = useAsyncState<MatchDetail>()
const dataQuality = useAsyncState<DataQualityRow[]>()
const scorelines = useAsyncState<ScorelineRow[]>()

const matchNo = computed(() => Number(route.params.matchNo ?? 1))
const matchTitle = computed(() => {
  const match = detail.data.value?.match
  return match ? `${match.home_team_zh} vs ${match.away_team_zh}` : '比赛分析'
})

const currentQuality = computed(() => {
  return (dataQuality.data.value ?? []).find((row) => row.match_no === matchNo.value) ?? null
})

const topScoreline = computed(() => scorelines.data.value?.[0] ?? null)
const actualScoreline = computed(() => {
  const match = detail.data.value?.match
  if (!match?.completed) {
    return null
  }
  if (match.actual_home_score == null || match.actual_away_score == null) {
    return null
  }
  return `${match.actual_home_score}-${match.actual_away_score}`
})

const predictedOutcomeLabel = computed(() => {
  const outcome = detail.data.value?.match.predicted_outcome
  if (outcome === 'home_win') {
    return '主胜'
  }
  if (outcome === 'draw') {
    return '平局'
  }
  if (outcome === 'away_win') {
    return '客胜'
  }
  return '暂无'
})

const outcomeHitLabel = computed(() => {
  const match = detail.data.value?.match
  if (!match?.completed || match.actual_home_score == null || match.actual_away_score == null) {
    return '待赛果'
  }

  const predicted = match.predicted_outcome
  const actual =
    match.actual_home_score > match.actual_away_score
      ? 'home_win'
      : match.actual_home_score < match.actual_away_score
        ? 'away_win'
        : 'draw'

  return predicted === actual ? '命中' : '未命中'
})

const exactScoreHitLabel = computed(() => {
  if (!actualScoreline.value || !topScoreline.value) {
    return '待赛果'
  }
  return topScoreline.value.scoreline === actualScoreline.value ? '命中' : '未命中'
})

function percent(value?: number | null) {
  return value == null ? '暂无' : `${(value * 100).toFixed(1)}%`
}

function loadPage() {
  detail.run(() => dashboardApi.matchDetail(matchNo.value))
  scorelines.run(() => dashboardApi.matchScorelines(matchNo.value, 10))
}

function selectMatch(nextMatchNo: number) {
  router.push(`/matches/${nextMatchNo}`)
}

onMounted(() => {
  if (!matchStore.matches.length) {
    matchStore.loadMatches()
  }
  dataQuality.run(dashboardApi.dataQuality)
  loadPage()
})

watch(matchNo, loadPage)
</script>

<template>
  <section class="page-stack">
    <header class="page-heading">
      <span class="eyebrow">Match Analysis</span>
      <h1>{{ matchTitle }}</h1>
      <p>展示比分概率、赔率价值和影响因素拆解，赛后同步展示预测与真实赛果对照。</p>
    </header>

    <MatchSwitcher
      :matches="matchStore.firstFourMatches"
      :active-match-no="matchNo"
      :loading="matchStore.loading"
      @select="selectMatch"
    />

    <ElAlert v-if="detail.error.value" :title="detail.error.value" type="error" show-icon />

    <div v-if="detail.data.value" class="stat-grid">
      <StatCard label="主胜概率" :value="percent(detail.data.value.outcome_probabilities.home_win)" />
      <StatCard label="平局概率" :value="percent(detail.data.value.outcome_probabilities.draw)" />
      <StatCard label="客胜概率" :value="percent(detail.data.value.outcome_probabilities.away_win)" />
    </div>

    <section v-if="detail.data.value" class="section-card">
      <div class="section-title">
        <h2>预测 vs 实际</h2>
        <span v-if="detail.data.value.match.completed">赛后复盘视角</span>
        <span v-else>赛前预测视角</span>
      </div>

      <div class="compare-grid">
        <article class="compare-card">
          <span class="compare-label">模型预测胜平负</span>
          <strong>{{ predictedOutcomeLabel }}</strong>
          <small>{{ outcomeHitLabel }}</small>
        </article>

        <article class="compare-card">
          <span class="compare-label">模型 Top 比分</span>
          <strong>{{ topScoreline?.scoreline ?? '暂无' }}</strong>
          <small>{{ exactScoreHitLabel }}</small>
        </article>

        <article class="compare-card">
          <span class="compare-label">真实比分</span>
          <strong>{{ actualScoreline ?? '待赛' }}</strong>
          <small>{{ detail.data.value.match.result_source_name ?? '暂无来源' }}</small>
        </article>
      </div>
    </section>

    <MatchCompletenessCard :quality="currentQuality" />

    <section v-if="detail.data.value" class="section-card">
      <div class="section-title">
        <h2>影响因素瀑布图</h2>
        <span>主队净修正视角</span>
      </div>
      <FactorWaterfall :factors="detail.data.value.factor_breakdown" />
    </section>

    <section class="section-card">
      <div class="section-title">
        <h2>Top 10 比分概率</h2>
        <span>{{ scorelines.loading.value ? '加载中...' : '含体彩赔率快照' }}</span>
      </div>
      <ScorelineProbabilityChart :rows="scorelines.data.value ?? []" />
      <ScorelineTable :rows="scorelines.data.value ?? []" />
    </section>
  </section>
</template>

<style scoped>
.compare-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.compare-card {
  display: grid;
  gap: 10px;
  padding: 18px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.72);
}

.compare-label {
  color: var(--color-muted);
  font-size: 13px;
}

.compare-card strong {
  font-size: 28px;
  line-height: 1.1;
}

.compare-card small {
  color: var(--color-muted);
  font-size: 13px;
}

@media (max-width: 900px) {
  .compare-grid {
    grid-template-columns: 1fr;
  }
}
</style>
