<script setup lang="ts">
import * as echarts from 'echarts'
import { nextTick, onBeforeUnmount, onMounted, shallowRef, useTemplateRef, watch } from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

interface EloItem {
  team_name: string
  team_name_zh: string
  elo: number
  matches_played: number
}

const chartRef = useTemplateRef<HTMLDivElement>('chart')
const chart = shallowRef<echarts.ECharts | null>(null)
const data = shallowRef<EloItem[]>([])
const loading = shallowRef(true)

async function load() {
  try {
    const resp = await fetch(`${API_BASE}/api/elo/distribution`)
    data.value = await resp.json()
  } catch {
    data.value = []
  } finally {
    loading.value = false
  }
}

function buildOption(items: EloItem[]) {
  const top30 = items.slice(0, 30).reverse()
  const minElo = Math.floor(top30[0]?.elo ?? 1500)
  const maxElo = Math.ceil(top30[top30.length - 1]?.elo ?? 2000)

  return {
    tooltip: {
      formatter: (params: { name: string; value: number }) =>
        `${params.name}: ${params.value.toFixed(0)}`,
    },
    grid: { left: 100, right: 40, top: 10, bottom: 30 },
    xAxis: { type: 'value', min: minElo - 30, max: maxElo + 30 },
    yAxis: {
      type: 'category',
      data: top30.map((t) => t.team_name_zh),
      axisLabel: { fontSize: 11, color: '#8899aa' },
    },
    series: [
      {
        type: 'bar',
        data: top30.map((t) => ({
          value: t.elo,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: '#2d756d' },
              { offset: 1, color: '#d4a843' },
            ]),
            borderRadius: [0, 4, 4, 0],
          },
        })),
        barWidth: 16,
      },
    ],
  }
}

let initialized = false

async function render() {
  await nextTick()
  if (!chartRef.value) return
  if (!initialized) {
    chart.value = echarts.init(chartRef.value)
    initialized = true
  }
  chart.value?.setOption(buildOption(data.value), { notMerge: true })
}

onMounted(async () => {
  await load()
  render()
  window.addEventListener('resize', render)
})

watch(data, render)

onBeforeUnmount(() => {
  window.removeEventListener('resize', render)
  chart.value?.dispose()
})
</script>

<template>
  <section class="section-card">
    <div class="section-title">
      <h2>世界杯 48 强 Elo 分布（前 30）</h2>
      <span v-if="loading">加载中...</span>
      <span v-else>历史比赛数据积累的实力评级</span>
    </div>
    <div ref="chart" class="chart" />
  </section>
</template>

<style scoped>
.chart {
  width: 100%;
  min-height: 580px;
}
</style>
