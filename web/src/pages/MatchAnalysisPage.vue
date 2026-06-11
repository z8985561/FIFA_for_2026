<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'

import FactorWaterfall from '@/components/match/FactorWaterfall.vue'
import ScorelineTable from '@/components/match/ScorelineTable.vue'
import StatCard from '@/components/common/StatCard.vue'
import { useAsyncState } from '@/composables/useAsyncState'
import { dashboardApi } from '@/services/api'
import type { MatchDetail, ScorelineRow } from '@/types/api'

const route = useRoute()
const detail = useAsyncState<MatchDetail>()
const scorelines = useAsyncState<ScorelineRow[]>()

const matchNo = computed(() => Number(route.params.matchNo ?? 1))
const matchTitle = computed(() => {
  const match = detail.data.value?.match
  return match ? `${match.home_team_zh} vs ${match.away_team_zh}` : '比赛分析'
})

function percent(value?: number | null) {
  return value == null ? '暂无' : `${(value * 100).toFixed(1)}%`
}

function loadPage() {
  detail.run(() => dashboardApi.matchDetail(matchNo.value))
  scorelines.run(() => dashboardApi.matchScorelines(matchNo.value, 10))
}

onMounted(loadPage)
watch(matchNo, loadPage)
</script>

<template>
  <section class="page-stack">
    <header class="page-heading">
      <span class="eyebrow">Match Analysis</span>
      <h1>{{ matchTitle }}</h1>
      <p>展示比分概率、赔率价值和影响因素拆解。所有结果按 90 分钟常规时间口径理解。</p>
    </header>

    <ElAlert v-if="detail.error.value" :title="detail.error.value" type="error" show-icon />

    <div v-if="detail.data.value" class="stat-grid">
      <StatCard
        label="主胜概率"
        :value="percent(detail.data.value.outcome_probabilities.home_win)"
      />
      <StatCard
        label="平局概率"
        :value="percent(detail.data.value.outcome_probabilities.draw)"
      />
      <StatCard
        label="客胜概率"
        :value="percent(detail.data.value.outcome_probabilities.away_win)"
      />
    </div>

    <section v-if="detail.data.value" class="section-card">
      <div class="section-title">
        <h2>影响因素瀑布图</h2>
        <span>主队净修正视角</span>
      </div>
      <FactorWaterfall :factors="detail.data.value.factor_breakdown" />
    </section>

    <section class="section-card">
      <div class="section-title">
        <h2>Top 10 得分比概率</h2>
        <span>{{ scorelines.loading.value ? '加载中...' : '含体彩赔率快照' }}</span>
      </div>
      <ScorelineTable :rows="scorelines.data.value ?? []" />
    </section>
  </section>
</template>
