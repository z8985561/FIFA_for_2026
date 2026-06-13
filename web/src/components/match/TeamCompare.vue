<script setup lang="ts">
import * as echarts from 'echarts'
import { computed, nextTick, onBeforeUnmount, onMounted, shallowRef, useTemplateRef, watch } from 'vue'

import { dashboardApi } from '@/services/api'
import type { TeamCompareItem, TeamCompareResponse } from '@/types/api'

const props = defineProps<{
  teamA: string
  teamB: string
}>()

const chartRef = useTemplateRef<HTMLDivElement>('chart')
const chart = shallowRef<echarts.ECharts | null>(null)
const data = shallowRef<TeamCompareResponse | null>(null)
const loading = shallowRef(false)

const indicators = [
  { name: 'Elo', max: 2200 },
  { name: '排名↓', max: 50 },
  { name: '阵容', max: 30 },
  { name: '年龄', max: 35 },
  { name: '出场', max: 1500 },
  { name: '出线率', max: 1 },
]

function buildRadarData(a: TeamCompareItem, b: TeamCompareItem) {
  return [
    {
      name: a.team_name_zh,
      value: [
        a.elo ?? 0,
        (50 - (a.fifa_rank ?? 50)),
        a.squad_size ?? 0,
        a.average_age ?? 0,
        a.total_caps ?? 0,
        a.group_advance_probability ?? 0,
      ],
      lineStyle: { color: '#c85848', width: 2 },
      areaStyle: { color: 'rgba(200, 88, 72, 0.12)' },
      itemStyle: { color: '#c85848' },
    },
    {
      name: b.team_name_zh,
      value: [
        b.elo ?? 0,
        (50 - (b.fifa_rank ?? 50)),
        b.squad_size ?? 0,
        b.average_age ?? 0,
        b.total_caps ?? 0,
        b.group_advance_probability ?? 0,
      ],
      lineStyle: { color: '#2d756d', width: 2 },
      areaStyle: { color: 'rgba(45, 117, 109, 0.12)' },
      itemStyle: { color: '#2d756d' },
    },
  ]
}

function buildOption(resp: TeamCompareResponse | null) {
  const series = resp ? buildRadarData(resp.team_a, resp.team_b) : []
  return {
    tooltip: {},
    legend: {
      data: series.map((d) => d.name),
      bottom: 0,
    },
    radar: {
      indicator: indicators,
      center: ['50%', '52%'],
      radius: '62%',
    },
    series: [{ type: 'radar', data: series }],
  }
}

let _initialized = false

async function initOrUpdate() {
  await nextTick()
  if (!chartRef.value) return
  if (!_initialized) {
    chart.value = echarts.init(chartRef.value)
    _initialized = true
  }
  chart.value?.setOption(buildOption(data.value), { notMerge: true })
}

async function load() {
  if (!props.teamA || !props.teamB) return
  loading.value = true
  try {
    data.value = await dashboardApi.compareTeams(props.teamA, props.teamB)
  } catch {
    data.value = null
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await load()
  initOrUpdate()
  window.addEventListener('resize', initOrUpdate)
})

watch(data, () => {
  if (data.value) initOrUpdate()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', initOrUpdate)
  chart.value?.dispose()
})
</script>

<template>
  <section class="section-card">
    <div class="section-title">
      <h2>实力对比</h2>
      <span v-if="loading">加载中...</span>
      <span v-else-if="data">Elo / 排名 / 阵容</span>
      <span v-else>暂无数据</span>
    </div>

    <div ref="chart" class="chart" />

    <div v-if="data" class="stat-cards">
      <div class="stat-card">
        <span>场均进球</span>
        <div class="stat-row">
          <strong>{{ data.team_a.avg_goals_scored?.toFixed(1) ?? '-' }}</strong>
          <em>vs</em>
          <strong>{{ data.team_b.avg_goals_scored?.toFixed(1) ?? '-' }}</strong>
        </div>
      </div>
      <div class="stat-card">
        <span>场均失球</span>
        <div class="stat-row">
          <strong>{{ data.team_a.avg_goals_conceded?.toFixed(1) ?? '-' }}</strong>
          <em>vs</em>
          <strong>{{ data.team_b.avg_goals_conceded?.toFixed(1) ?? '-' }}</strong>
        </div>
      </div>
      <div class="stat-card">
        <span>场均射门</span>
        <div class="stat-row">
          <strong>{{ data.team_a.avg_shots?.toFixed(0) ?? '-' }}</strong>
          <em>vs</em>
          <strong>{{ data.team_b.avg_shots?.toFixed(0) ?? '-' }}</strong>
        </div>
      </div>
      <div class="stat-card">
        <span>场均犯规</span>
        <div class="stat-row">
          <strong>{{ data.team_a.avg_fouls?.toFixed(0) ?? '-' }}</strong>
          <em>vs</em>
          <strong>{{ data.team_b.avg_fouls?.toFixed(0) ?? '-' }}</strong>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.chart {
  width: 100%;
  min-height: 360px;
}

.stat-cards {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.stat-card {
  display: grid;
  gap: 6px;
  padding: 14px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  background: rgba(18, 35, 64, 0.5);
}

.stat-card span {
  color: var(--color-muted);
  font-size: 12px;
}

.stat-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stat-row strong {
  font-size: 18px;
}

.stat-row em {
  font-style: normal;
  color: var(--color-muted);
  font-size: 12px;
}

@media (max-width: 900px) {
  .stat-cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
