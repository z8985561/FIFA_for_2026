<script setup lang="ts">
import { onMounted } from 'vue'

import DataSnapshotBar from '@/components/common/DataSnapshotBar.vue'
import MatchCard from '@/components/match/MatchCard.vue'
import ScorelineTable from '@/components/match/ScorelineTable.vue'
import StatCard from '@/components/common/StatCard.vue'
import { useAsyncState } from '@/composables/useAsyncState'
import { dashboardApi } from '@/services/api'
import { useMatchStore } from '@/stores/match'
import type { HealthResponse, ScorelineRow } from '@/types/api'

const matchStore = useMatchStore()
const health = useAsyncState<HealthResponse>()
const valueRows = useAsyncState<ScorelineRow[]>()

onMounted(() => {
  matchStore.loadMatches()
  health.run(dashboardApi.health)
  valueRows.run(() => dashboardApi.valueScorelines(8, 'edge'))
})
</script>

<template>
  <section class="page-stack">
    <header class="hero">
      <span class="eyebrow">Research Dashboard MVP</span>
      <h1>用模型、赔率和解释链路拆解 2026 世界杯前四场。</h1>
      <p>
        当前版本只做研究分析和虚拟组合模拟，所有概率均来自本地模型产物与已入库赔率快照。
      </p>
    </header>

    <DataSnapshotBar />

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
        <h2>当前价值信号 Top 8</h2>
        <span>按市场边际排序</span>
      </div>
      <ScorelineTable :rows="valueRows.data.value ?? []" />
    </section>
  </section>
</template>
