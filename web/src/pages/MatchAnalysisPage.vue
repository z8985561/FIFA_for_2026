<script setup lang="ts">
import { computed, onMounted, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import PageNav from '@/components/common/PageNav.vue'
import StatCard from '@/components/common/StatCard.vue'
import FactorWaterfall from '@/components/match/FactorWaterfall.vue'
import MatchAnalysisSummary from '@/components/match/MatchAnalysisSummary.vue'
import MatchCompletenessCard from '@/components/match/MatchCompletenessCard.vue'
import MatchSwitcher from '@/components/match/MatchSwitcher.vue'
import MatchTechRadar from '@/components/match/MatchTechRadar.vue'
import TeamCompare from '@/components/match/TeamCompare.vue'
import ScorelineProbabilityChart from '@/components/match/ScorelineProbabilityChart.vue'
import PreMatchContextCard from '@/components/match/PreMatchContextCard.vue'
import ScorelineTable from '@/components/match/ScorelineTable.vue'
import TeamContextCard from '@/components/match/TeamContextCard.vue'
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

const navItems = [
  { id: 'sec-probabilities', label: '胜平负概率' },
  { id: 'sec-preview', label: '赛前情报' },
  { id: 'sec-team', label: '球队状态' },
  { id: 'sec-tech', label: '技术统计' },
  { id: 'sec-compare', label: '实力对比' },
  { id: 'sec-predictions', label: '预测 vs 实际' },
  { id: 'sec-insights', label: '偏差拆解' },
  { id: 'sec-quality', label: '数据完整性' },
  { id: 'sec-factors', label: '影响因素' },
  { id: 'sec-scorelines', label: 'Top 比分' },
]
const detail = useAsyncState<MatchDetail>()
const dataQuality = useAsyncState<DataQualityRow[]>()
const scorelines = useAsyncState<ScorelineRow[]>()

const matchNo = computed(() => Number(route.params.matchNo ?? 1))

// 明日北京日期字符串，用于 MatchSwitcher 标题
const tomorrowDateStr = computed(() => {
  const now = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Shanghai' }))
  const tomorrow = new Date(now)
  tomorrow.setDate(now.getDate() + 1)
  const y = tomorrow.getFullYear()
  const m = String(tomorrow.getMonth() + 1).padStart(2, '0')
  const d = String(tomorrow.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
})

const matchTitle = computed(() => {
  const match = detail.data.value?.match
  return match ? `${match.home_team_zh} vs ${match.away_team_zh}` : '比赛分析'
})

const currentQuality = computed(() => {
  return (dataQuality.data.value ?? []).find((row) => row.match_no === matchNo.value) ?? null
})

const topScoreline = computed(() => scorelines.data.value?.[0] ?? null)
const top3Scorelines = computed(() => scorelines.data.value?.slice(0, 3) ?? [])

const top3Hit = computed(() => {
  if (!actualScoreline.value || top3Scorelines.value.length === 0) return false
  return top3Scorelines.value.some((s) => s.scoreline === actualScoreline.value)
})

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
  if (!actualScoreline.value || top3Scorelines.value.length === 0) {
    return '待赛果'
  }
  return top3Hit.value ? '命中' : '未命中'
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

  if (top3Scorelines.value.length > 0 && actualScoreline.value) {
    const top3List = top3Scorelines.value.map((s) => s.scoreline).join('、')
    insights.push({
      title: '精确比分',
      verdict: top3Hit.value ? '比分命中' : '比分偏离',
      description: top3Hit.value
        ? `模型 Top 3 比分（${top3List}）中包含真实比分 ${actualScoreline.value}，预测命中。`
        : `模型 Top 3 比分为 ${top3List}，真实比分为 ${actualScoreline.value}，精确比分未命中。`,
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

const homeCompare = shallowRef<any>(null)
const awayCompare = shallowRef<any>(null)

function loadPage() {
  detail.run(() => dashboardApi.matchDetail(matchNo.value))
  scorelines.run(() => dashboardApi.matchScorelines(matchNo.value, 10))
}

async function loadCompare() {
  const d = detail.data.value
  if (!d?.match?.home_team || !d?.match?.away_team) return
  try {
    const resp = await dashboardApi.compareTeams(d.match.home_team, d.match.away_team)
    homeCompare.value = resp.team_a
    awayCompare.value = resp.team_b
  } catch { /* ignore */ }
}

// Watch for detail data arrival to load compare
watch(() => detail.data.value, () => {
  if (detail.data.value) loadCompare()
})

function selectMatch(nextMatchNo: number) {
  router.push(`/matches/${nextMatchNo}`)
}

function goSchedule() {
  router.push('/schedule')
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
    <div class="page-layout">
      <div class="page-content">

    <header class="page-heading">
      <span class="eyebrow">Match Analysis</span>
      <h1>{{ matchTitle }}</h1>
      <p>展示比分概率、赔率价值和影响因素拆解，赛后同步展示预测与真实赛果对照。</p>
    </header>

    <MatchSwitcher
      :matches="matchStore.tomorrowMatches"
      :active-match-no="matchNo"
      :loading="matchStore.loading"
      :tomorrow-date="tomorrowDateStr"
      @select="selectMatch"
      @go-schedule="goSchedule"
    />

    <ElAlert v-if="detail.error.value" :title="detail.error.value" type="error" show-icon />

    <div id="sec-probabilities" v-if="detail.data.value" class="stat-grid stat-grid-6">
      <StatCard label="主胜概率" :value="percent(detail.data.value.outcome_probabilities.home_win)" />
      <StatCard label="平局概率" :value="percent(detail.data.value.outcome_probabilities.draw)" />
      <StatCard label="客胜概率" :value="percent(detail.data.value.outcome_probabilities.away_win)" />
      <StatCard label="大 2.5" :value="percent(detail.data.value.outcome_probabilities.over_2_5)" />
      <StatCard label="小 2.5" :value="percent(detail.data.value.outcome_probabilities.under_2_5)" />
      <StatCard label="双方进球" :value="percent(detail.data.value.outcome_probabilities.both_teams_score)" />
    </div>

    <div id="sec-preview"><PreMatchContextCard :sources="detail.data.value?.preview_sources ?? []" /></div>

    <section id="sec-team" v-if="detail.data.value" class="section-card">
      <div class="section-title">
        <h2>球队状态</h2>
        <span>来自网易及赛前情报</span>
      </div>
      <div class="team-context-grid">
        <TeamContextCard
          :context="detail.data.value.home_team_context"
          side="home"
        />
        <TeamContextCard
          :context="detail.data.value.away_team_context"
          side="away"
        />
      </div>
    </section>

    <div id="sec-tech"><MatchTechRadar :tech="detail.data.value?.match_tech" /></div>

    <div id="sec-compare"><TeamCompare
      :team-a="detail.data.value?.match?.home_team ?? ''"
      :team-b="detail.data.value?.match?.away_team ?? ''"
    /></div>

    <MatchAnalysisSummary
      v-if="detail.data.value"
      :detail="detail.data.value"
      :home-compare="homeCompare"
      :away-compare="awayCompare"
    />

    <section id="sec-predictions" v-if="detail.data.value" class="section-card">
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
          <div class="top3-scores">
            <span
              v-for="(s, i) in top3Scorelines"
              :key="s.scoreline"
              class="top3-item"
              :class="{
                'top3-hit': actualScoreline && s.scoreline === actualScoreline,
                'top3-miss': actualScoreline && s.scoreline !== actualScoreline,
              }"
            >
              <em>{{ i + 1 }}</em>{{ s.scoreline }}
              <small>{{ (s.model_probability * 100).toFixed(1) }}%</small>
            </span>
            <span v-if="top3Scorelines.length === 0" class="muted">暂无</span>
          </div>
          <small :class="top3Hit ? 'hit-label' : ''">{{ exactScoreHitLabel }}</small>
        </article>

        <article class="compare-card">
          <span class="compare-label">真实比分</span>
          <strong>{{ actualScoreline ?? '待赛' }}</strong>
          <small>{{ detail.data.value.match.result_source_name ?? '暂无来源' }}</small>
        </article>
      </div>
    </section>

    <section id="sec-insights" v-if="detail.data.value && detail.data.value.match.completed && biasInsights.length" class="section-card">
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

    <div id="sec-quality"><MatchCompletenessCard :quality="currentQuality" /></div>

    <section id="sec-factors" v-if="detail.data.value" class="section-card">
      <div class="section-title">
        <h2>影响因素瀑布图</h2>
        <span>主队净修正视角</span>
      </div>
      <FactorWaterfall :factors="detail.data.value.factor_breakdown" />
    </section>

    <section id="sec-scorelines" class="section-card">
      <div class="section-title">
        <h2>Top 10 比分概率</h2>
        <span>{{ scorelines.loading.value ? '加载中...' : '含体彩赔率快照' }}</span>
      </div>
      <ScorelineProbabilityChart :rows="scorelines.data.value ?? []" />
      <ScorelineTable :rows="scorelines.data.value ?? []" />
    </section>
      </div>
      <PageNav :items="navItems" />
    </div>
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

.stat-grid-6 {
  grid-template-columns: repeat(6, minmax(0, 1fr));
}

.team-context-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

@media (max-width: 900px) {
  .stat-grid-6 {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .team-context-grid {
    grid-template-columns: 1fr;
  }

  .compare-grid,
  .insight-grid {
    grid-template-columns: 1fr;
  }
}

.top3-scores {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 6px 0;
}

.top3-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background 0.15s;
}

.top3-item em {
  font-style: normal;
  font-size: 11px;
  color: var(--color-muted);
  min-width: 14px;
}

.top3-item small {
  font-size: 12px;
  font-weight: 400;
  color: var(--color-muted);
  margin-left: auto;
}

.top3-hit {
  background: rgba(34, 197, 94, 0.15);
  color: #16a34a;
}

.top3-miss {
  color: var(--color-ink);
}

.hit-label {
  color: #16a34a;
  font-weight: 600;
}
.page-layout {
  display: grid;
  grid-template-columns: 1fr 180px;
  gap: 28px;
  align-items: start;
}

.page-content {
  min-width: 0;
}

@media (max-width: 1280px) {
  .page-layout {
    grid-template-columns: 1fr;
  }
}

</style>
