<script setup lang="ts">
import type { ScorelineRow } from '@/types/api'

defineProps<{
  rows: readonly ScorelineRow[]
  showMatch?: boolean
}>()

function percent(value?: number | null) {
  return value == null ? '暂无' : `${(value * 100).toFixed(2)}%`
}

function numberText(value?: number | null, digits = 2) {
  return value == null ? '暂无' : value.toFixed(digits)
}

function signalLabel(signal: string) {
  const labels: Record<string, string> = {
    strong_value: '强价值',
    thin_value: '薄价值',
    no_value: '无价值',
    missing_odds: '缺赔率',
  }
  return labels[signal] ?? signal
}
</script>

<template>
  <ElTable :data="rows" class="scoreline-table">
    <ElTableColumn v-if="showMatch" label="比赛" min-width="180">
      <template #default="{ row }">
        第 {{ row.match_no }} 场
        <strong>{{ row.home_team_zh ?? row.home_team }}</strong>
        vs
        <strong>{{ row.away_team_zh ?? row.away_team }}</strong>
      </template>
    </ElTableColumn>
    <ElTableColumn prop="scoreline_rank" label="排名" width="80" />
    <ElTableColumn prop="scoreline" label="比分" width="100" />
    <ElTableColumn label="模型概率">
      <template #default="{ row }">{{ percent(row.model_probability) }}</template>
    </ElTableColumn>
    <ElTableColumn label="公平赔率">
      <template #default="{ row }">{{ numberText(row.model_fair_odds) }}</template>
    </ElTableColumn>
    <ElTableColumn label="市场赔率">
      <template #default="{ row }">{{ numberText(row.best_decimal_odds) }}</template>
    </ElTableColumn>
    <ElTableColumn label="市场边际">
      <template #default="{ row }">{{ percent(row.market_edge) }}</template>
    </ElTableColumn>
    <ElTableColumn label="信号">
      <template #default="{ row }">
        <ElTag :type="row.value_signal === 'strong_value' ? 'danger' : 'info'" effect="plain">
          {{ signalLabel(row.value_signal) }}
        </ElTag>
      </template>
    </ElTableColumn>
  </ElTable>
</template>

<style scoped>
.scoreline-table {
  width: 100%;
  border-radius: var(--radius-md);
  overflow: hidden;
}
</style>
