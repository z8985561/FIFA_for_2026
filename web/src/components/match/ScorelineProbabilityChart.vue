<script setup lang="ts">
import * as echarts from 'echarts'
import { computed, onBeforeUnmount, onMounted, shallowRef, useTemplateRef, watch } from 'vue'

import type { ScorelineRow } from '@/types/api'

const props = defineProps<{
  rows: readonly ScorelineRow[]
}>()

const chartRef = useTemplateRef<HTMLDivElement>('chart')
const chart = shallowRef<echarts.ECharts | null>(null)

function percent(value?: number | null, digits = 2) {
  return value == null ? '暂无' : `${(value * 100).toFixed(digits)}%`
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

function signalColor(signal: string) {
  if (signal === 'strong_value') {
    return '#c85848'
  }
  if (signal === 'missing_odds') {
    return '#b8b3a9'
  }
  return '#2d756d'
}

const option = computed<echarts.EChartsOption>(() => {
  const rows = props.rows.slice(0, 10)

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: unknown) => {
        const item = Array.isArray(params) ? params[0] : params
        const data = (item as { data?: ScorelineRow }).data
        if (!data) {
          return ''
        }

        return [
          `<strong>${data.scoreline}</strong>`,
          `模型概率：${percent(data.model_probability)}`,
          `公平赔率：${numberText(data.model_fair_odds)}`,
          `市场赔率：${data.best_decimal_odds == null ? '暂未获取赔率' : numberText(data.best_decimal_odds)}`,
          `价值信号：${signalLabel(data.value_signal)}`,
        ].join('<br/>')
      },
    },
    grid: { left: 42, right: 20, top: 24, bottom: 52 },
    xAxis: {
      type: 'category',
      data: rows.map((row) => row.scoreline),
      axisLabel: { interval: 0 },
    },
    yAxis: {
      type: 'value',
      name: '模型概率',
      axisLabel: {
        formatter: (value: number) => `${(value * 100).toFixed(0)}%`,
      },
    },
    series: [
      {
        type: 'bar',
        data: rows.map((row) => ({
          value: row.model_probability,
          itemStyle: {
            color: signalColor(row.value_signal),
            opacity: row.value_signal === 'missing_odds' ? 0.55 : 0.95,
          },
          ...row,
        })),
        barMaxWidth: 44,
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
  <section class="chart-panel">
    <div ref="chart" class="chart" />
    <div class="legend-row">
      <span class="legend-item">
        <i class="legend-dot legend-dot--strong" />
        强价值
      </span>
      <span class="legend-item">
        <i class="legend-dot legend-dot--normal" />
        常规
      </span>
      <span class="legend-item">
        <i class="legend-dot legend-dot--missing" />
        暂未获取赔率
      </span>
    </div>
  </section>
</template>

<style scoped>
.chart-panel {
  display: grid;
  gap: 12px;
}

.chart {
  width: 100%;
  min-height: 320px;
}

.legend-row {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  color: var(--color-muted);
  font-size: 13px;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
}

.legend-dot--strong {
  background: #c85848;
}

.legend-dot--normal {
  background: #2d756d;
}

.legend-dot--missing {
  background: #b8b3a9;
}
</style>
