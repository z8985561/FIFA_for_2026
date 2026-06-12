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

interface BiasInsight {
  title: string
  verdict: string
  description: string
}

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

const actualOutcomeKey = computed(() => {
  const match = detail.data.value?.match
  if (!match?.completed || match.actual_home_score == null || match.actual_away_score == null) {
    return null
  }
  if (match.actual_home_score > match.actual_away_score) {
    return 'home_win'
  }
  if (match.actual_home_score < match.actual_away_score) {
    return 'away_win'
  }
  return 'draw'
})

const predictedOutcomeLabel = computed(() => outcomeLabel(detail.data.value?.match.predicted_outcome))
const actualOutcomeLabel = computed(() => outcomeLabel(actualOutcomeKey.value))

const outcomeHitLabel = computed(() => {
  const predicted = detail.data.value?.match.predicted_outcome
  const actual = actualOutcomeKey.value
  if (!predicted || !actual) {
    return '待赛果'
  }
  return predicted === actual ? '命中' : '未命中'
})

const exactScoreHitLabel = computed(() => {
  if (!actualScoreline.value || !topScoreline.value) {
    return '待赛果'
  }
  return topScoreline.value.scoreline === actualScoreline.value ? '命中' : '未命中'
})

const expectedTotalGoals = computed(() => {
  const expected = detail.data.value?.expected_goals
  if (!expected) {
    return null
  }
  const home = expected.home_final ?? expected.home_raw
  const away = expected.away_final ?? expected.away_raw
  if (home == null || away == null) {
    return null
  }
  return home + away
})

const actualTotalGoals = computed(() => {
  const match = detail.data.value?.match
  if (!match?.completed || match.actual_home_score == null || match.actual_away_score == null) {
    return null
  }
  return match.actual_home_score + match.actual_away_score
})

const biasInsights = computed<BiasInsight[]>(() => {
  const match = detail.data.value?.match
  if (!match?.completed || match.actual_home_score == null || match.actual_away_score == null) {
    return []
  }

  const insights: BiasInsight[] = []
  const predictedOutcome = match.predicted_outcome
  const actualOutcome = actualOutcomeKey.value

  if (predictedOutcome && actualOutcome) {
    insights.push({
      title: '胜平负判断',
      verdict: predictedOutcome === actualOutcome ? '方向命中' : '方向偏离',
      description:
        predictedOutcome === actualOutcome
          ? `模型判断为${outcomeLabel(predictedOutcome)}，真实赛果同样为${outcomeLabel(actualOutcome)}。`
          : `模型判断为${outcomeLabel(predictedOutcome)}，但真实赛果为${outcomeLabel(actualOutcome)}，说明比赛方向判断出现偏差。`,
    })
  }

  if (topScoreline.value && actualScoreline.value) {
    insights.push({
      title: '精确比分',
      verdict: topScoreline.value.scoreline === actualScoreline.value ? '比分命中' : '比分偏离',
      description:
        topScoreline.value.scoreline === actualScoreline.value
          ? `模型最高概率比分是 ${topScoreline.value.scoreline}，与真实比分完全一致。`
          : `模型最高概率比分是 ${topScoreline.value.scoreline}，真实比分为 ${actualScoreline.value}，精确比分没有命中。`,
    })
  }

  if (expectedTotalGoals.value != null && actualTotalGoals.value != null) {
    const delta = actualTotalGoals.value - expectedTotalGoals.value
    const verdict =
      Math.abs(delta) < 0.35
        ? '进球节奏接近预期'
        : delta > 0
          ? '比赛比预期更开放'
          : '比赛比预期更保守'

    insights.push({
      title: '总进球节奏',
      verdict,
      description: `模型预期总进球约 ${expectedTotalGoals.value.toFixed(2)}，实际总进球为 ${actualTotalGoals.value}，偏差 ${delta >= 0 ? '+' : ''}${delta.toFixed(2)}。`,
    })
  }

  const matchProbabilities = detail.data.value?.outcome_probabilities
  if (matchProbabilities && actualOutcome) {
    const predictedProb =
      actualOutcome === 'home_win'
        ? matchProbabilities.home_win
        : actualOutcome === 'draw'
          ? matchProbabilities.draw
          : matchProbabilities.away_win

    if (predictedProb != null) {
      insights.push({
        title: '真实结果置信度',
        verdict: predictedProb >= 0.45 ? '模型对真实结果有一定覆盖' : '模型低估了真实结果',
        description: `模型给真实结果方向的赛前概率是 ${(predictedProb * 100).toFixed(1)}%。这个数值越低，说明赛前越难从基础模型中直接看出真实走向。`,
      })
    }
  }

  return insights
})

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

    <section v-if="detail.data.value && detail.data.value.match.completed && biasInsights.length" class="section-card">
      <div class="section-title">
        <h2>预测偏差拆解</h2>
        <span>白盒解释模型偏差来自哪里</span>
      </div>

      <div class="insight-grid">
        <article v-for="insight in biasInsights" :key="insight.title" class="insight-card">
          <div class="insight-head">
            <span class="insight-title">{{ insight.title }}</span>
            <strong>{{ insight.verdict }}</strong>
          </div>
          <p>{{ insight.description }}</p>
        </article>
      </div>

      <div class="summary-strip">
        <span>真实赛果方向：{{ actualOutcomeLabel }}</span>
        <span>模型预期总进球：{{ expectedTotalGoals == null ? '暂无' : expectedTotalGoals.toFixed(2) }}</span>
        <span>实际总进球：{{ actualTotalGoals ?? '暂无' }}</span>
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
.compare-grid,
.insight-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.compare-card,
.insight-card {
  display: grid;
  gap: 10px;
  padding: 18px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.72);
}

.compare-label,
.insight-title {
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

.insight-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.insight-head strong {
  font-size: 15px;
}

.insight-card p {
  margin: 0;
  color: var(--color-ink);
  line-height: 1.6;
}

.summary-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 16px;
  color: var(--color-muted);
  font-size: 13px;
}

@media (max-width: 900px) {
  .compare-grid,
  .insight-grid {
    grid-template-columns: 1fr;
  }
}
</style>
