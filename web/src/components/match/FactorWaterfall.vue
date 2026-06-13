<script setup lang="ts">
import * as echarts from 'echarts'
import { computed, onBeforeUnmount, onMounted, shallowRef, useTemplateRef, watch } from 'vue'

import type { FactorBreakdown } from '@/types/api'

const props = defineProps<{
  factors: readonly FactorBreakdown[]
}>()

const chartRef = useTemplateRef<HTMLDivElement>('chart')
const chart = shallowRef<echarts.ECharts | null>(null)

const option = computed(() => {
  const labels = props.factors.map((factor) => factor.factor)
  const values = props.factors.map((factor) => {
    return (factor.home_delta_goals ?? 0) - (factor.away_delta_goals ?? 0)
  })

  return {
    tooltip: {
      trigger: 'axis',
      valueFormatter: (value: number) => value.toFixed(3),
    },
    grid: { left: 42, right: 18, top: 24, bottom: 70 },
    xAxis: {
      type: 'category',
      data: labels,
      axisLabel: { interval: 0, rotate: 22 },
    },
    yAxis: {
      type: 'value',
      name: '主队净修正',
    },
    series: [
      {
        type: 'bar',
        data: values,
        itemStyle: {
          color: (params: { value: number }) =>
            params.value >= 0 ? '#c85848' : '#2d756d',
        },
      },
    ],
  }
})

function renderChart() {
  if (!chartRef.value) {
    return
  }
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
  <section class="factor-panel">
    <div ref="chart" class="chart" />
    <ul class="factor-list">
      <li v-for="factor in factors" :key="factor.factor">
        <strong>{{ factor.factor }}</strong>
        <span>{{ factor.description }}</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.factor-panel {
  display: grid;
  gap: 18px;
}

.chart {
  width: 100%;
  min-height: 320px;
}

.factor-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.factor-list li {
  display: grid;
  gap: 4px;
  padding: 14px;
  border-radius: var(--radius-md);
  background: rgba(18, 35, 64, 0.5);
}

.factor-list span {
  color: var(--color-muted);
  line-height: 1.6;
}
</style>
