<script setup lang="ts">
import * as echarts from 'echarts'
import { computed, nextTick, onBeforeUnmount, onMounted, shallowRef, useTemplateRef, watch } from 'vue'

import type { MatchTechStats } from '@/types/api'

const props = defineProps<{
  tech: MatchTechStats | null | undefined
}>()

const chartRef = useTemplateRef<HTMLDivElement>('chart')
const chart = shallowRef<echarts.ECharts | null>(null)

const indicators = [
  { name: '控球率', max: 100 },
  { name: '射门', max: 20 },
  { name: '射正', max: 10 },
  { name: '角球', max: 10 },
  { name: '黄牌', max: 6 },
  { name: '红牌', max: 2 },
]

function buildSeries(tech: MatchTechStats) {
  return [
    {
      name: '主队',
      value: [
        tech.home_possession,
        tech.home_shots,
        tech.home_shots_on_target,
        tech.home_corners,
        tech.home_yellow_cards,
        tech.home_red_cards,
      ],
      lineStyle: { color: '#c85848', width: 2 },
      areaStyle: { color: 'rgba(200, 88, 72, 0.12)' },
      itemStyle: { color: '#c85848' },
    },
    {
      name: '客队',
      value: [
        tech.away_possession,
        tech.away_shots,
        tech.away_shots_on_target,
        tech.away_corners,
        tech.away_yellow_cards,
        tech.away_red_cards,
      ],
      lineStyle: { color: '#2d756d', width: 2 },
      areaStyle: { color: 'rgba(45, 117, 109, 0.12)' },
      itemStyle: { color: '#2d756d' },
    },
  ]
}

function buildOption(tech: MatchTechStats | null | undefined) {
  const data = tech ? buildSeries(tech) : []
  return {
    tooltip: {},
    legend: {
      data: data.map((d) => d.name),
      bottom: 0,
    },
    radar: {
      indicator: indicators,
      center: ['50%', '52%'],
      radius: '62%',
    },
    series: [{ type: 'radar', data }],
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

  chart.value?.setOption(buildOption(props.tech), { notMerge: true })
}

onMounted(() => {
  initOrUpdate()
  window.addEventListener('resize', initOrUpdate)
})

watch(() => props.tech, () => {
  if (props.tech) {
    initOrUpdate()
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', initOrUpdate)
  chart.value?.dispose()
})
</script>

<template>
  <section class="section-card">
    <div class="section-title">
      <h2>技术统计对比</h2>
      <span v-if="props.tech">来自网易体育</span>
      <span v-else>暂无数据</span>
    </div>
    <div ref="chart" class="chart" />
  </section>
</template>

<style scoped>
.chart {
  width: 100%;
  min-height: 380px;
}
</style>
