<script setup lang="ts">
import { onMounted } from 'vue'

import DataSnapshotBar from '@/components/common/DataSnapshotBar.vue'
import StatCard from '@/components/common/StatCard.vue'
import HomeCompletenessSummary from '@/components/home/HomeCompletenessSummary.vue'
import MatchReviewInsight from '@/components/home/MatchReviewInsight.vue'
import RecentResultsReview from '@/components/home/RecentResultsReview.vue'
import MatchCard from '@/components/match/MatchCard.vue'
import ScorelineTable from '@/components/match/ScorelineTable.vue'
import { useAsyncState } from '@/composables/useAsyncState'
import { dashboardApi } from '@/services/api'
import { useMatchStore } from '@/stores/match'
import type { DataQualityRow, HealthResponse, MatchReviewRow, ScorelineRow } from '@/types/api'

const matchStore = useMatchStore()
const health = useAsyncState<HealthResponse>()
const dataQuality = useAsyncState<DataQualityRow[]>()
const valueRows = useAsyncState<ScorelineRow[]>()
const matchReviews = useAsyncState<MatchReviewRow[]>()

onMounted(() => {
  matchStore.loadMatches()
  health.run(dashboardApi.health)
  dataQuality.run(dashboardApi.dataQuality)
  valueRows.run(() => dashboardApi.valueScorelines(8, 'edge'))
  matchReviews.run(() => dashboardApi.matchReviews(8))
})
</script>

<template>
  <section class="page-stack">
    <header class="hero">
      <span class="eyebrow">Research Dashboard MVP</span>
      <h1>用模型、赔率和解释链路拆解 2026 世界杯重点比赛。</h1>
      <p>当前版本聚焦研究分析与赛后复盘，所有概率均来自本地模型产物与已入库赔率快照。</p>
    </header>

    <DataSnapshotBar />

    <HomeCompletenessSummary
      :rows="dataQuality.data.value ?? []"
      :focus-matches="matchStore.firstFourMatches"
      :loading="dataQuality.loading.value"
      :error="dataQuality.error.value"
    />

    <div class="stat-grid">
      <StatCard
        label="比赛预测行数"
        :value="String(health.data.value?.row_counts.enhanced_predictions ?? '加载中')"
        hint="来自 enhanced predictions"
      />
      <StatCard
        label="比分概率行数"
        :value="String(health.data.value?.row_counts.scorelines ?? '加载中')"
        hint="Dixon-Coles + 修正因子"
      />
      <StatCard
        label="价值信号行数"
        :value="String(health.data.value?.row_counts.value_bets ?? '加载中')"
        hint="模型概率 vs 市场赔率"
      />
    </div>

    <section class="section-card">
      <div class="section-title">
        <h2>前四场重点比赛</h2>
        <span v-if="matchStore.loading">加载中...</span>
      </div>
      <div class="match-grid">
        <MatchCard
          v-for="match in matchStore.firstFourMatches"
          :key="match.match_no"
          :match="match"
        />
      </div>
    </section>

    <section class="section-card">
      <div class="section-title">
        <h2>最新赛果复盘</h2>
        <span>在首页快速查看预测与真实结果的偏差</span>
      </div>
      <RecentResultsReview :matches="matchStore.recentCompletedMatches" />
    </section>

    <MatchReviewInsight :reviews="matchReviews.data.value ?? []" />

    <section class="section-card">
      <div class="section-title">
        <h2>当前价值信号 Top 8</h2>
        <span>按市场边际排序</span>
      </div>
      <ScorelineTable :rows="valueRows.data.value ?? []" />
    </section>
  </section>
</template>
