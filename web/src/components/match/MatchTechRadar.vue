<script setup lang="ts">
import * as echarts from 'echarts'
import { computed, onBeforeUnmount, onMounted, shallowRef, useTemplateRef, watch } from 'vue'

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

const homeData = computed(() => {
  if (!props.tech) return { name: '主队', value: [] as number[] }
  return {
    name: '主队',
    value: [
      props.tech.home_possession,
      props.tech.home_shots,
      props.tech.home_shots_on_target,
      props.tech.home_corners,
      props.tech.home_yellow_cards,
      props.tech.home_red_cards,
    ],
  }
})

const awayData = computed(() => {
  if (!props.tech) return { name: '客队', value: [] as number[] }
  return {
    name: '客队',
    value: [
      props.tech.away_possession,
      props.tech.away_shots,
      props.tech.away_shots_on_target,
      props.tech.away_corners,
      props.tech.away_yellow_cards,
      props.tech.away_red_cards,
    ],
  }
})

const option = computed(() => ({
  tooltip: {},
  legend: {
    data: [homeData.value.name, awayData.value.name],
    bottom: 0,
  },
  radar: {
    indicator: indicators,
    center: ['50%', '52%'],
    radius: '62%',
  },
  series: [
    {
      type: 'radar',
      data: [
        {
          ...homeData.value,
          lineStyle: { color: '#c85848', width: 2 },
          areaStyle: { color: 'rgba(200, 88, 72, 0.12)' },
          itemStyle: { color: '#c85848' },
        },
        {
          ...awayData.value,
          lineStyle: { color: '#2d756d', width: 2 },
          areaStyle: { color: 'rgba(45, 117, 109, 0.12)' },
          itemStyle: { color: '#2d756d' },
        },
      ],
    },
  ],
}))

function renderChart() {
  if (!chartRef.value) return
  chart.value ??= echarts.init(chartRef.value)
  chart.value.setOption(option.value)
}

onMounted(() => {
  renderChart()
  window.addEventListener('resize', renderChart)
})

watch(option, renderChart)

onBeforeUnmount(() => {
  window.removeEventListener('resize', renderChart)
  chart.value?.dispose()
})
</script>

<template>
  <section v-if="props.tech" class="section-card">
    <div class="section-title">
      <h2>技术统计对比</h2>
      <span>来自网易体育</span>
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
