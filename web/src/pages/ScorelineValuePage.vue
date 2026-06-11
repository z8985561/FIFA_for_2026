<script setup lang="ts">
import { computed, onMounted, shallowRef } from 'vue'

import DataSnapshotBar from '@/components/common/DataSnapshotBar.vue'
import ScorelineTable from '@/components/match/ScorelineTable.vue'
import StatCard from '@/components/common/StatCard.vue'
import { useAsyncState } from '@/composables/useAsyncState'
import { dashboardApi } from '@/services/api'
import type { ScorelineRow } from '@/types/api'

const rows = useAsyncState<ScorelineRow[]>()
const activeSignal = shallowRef('')
const sortBy = shallowRef('edge')

const signalOptions = [
  { label: '全部', value: '' },
  { label: '强价值', value: 'strong_value' },
  { label: '薄价值', value: 'thin_value' },
  { label: '无价值', value: 'no_value' },
  { label: '缺赔率', value: 'missing_odds' },
]

const strongValueRows = computed(() => {
  return (rows.data.value ?? []).filter((row) => row.value_signal === 'strong_value')
})

const bestEdge = computed(() => {
  const edges = (rows.data.value ?? [])
    .map((row) => row.market_edge)
    .filter((edge): edge is number => edge != null)
  return edges.length ? Math.max(...edges) : null
})

function percent(value?: number | null, digits = 1) {
  return value == null ? '暂无' : `${(value * 100).toFixed(digits)}%`
}

function loadRows() {
  rows.run(() => {
    const signal = activeSignal.value || undefined
    return dashboardApi.valueScorelines(50, sortBy.value, signal)
  })
}

onMounted(loadRows)
</script>

<template>
  <section class="page-stack">
    <header class="page-heading">
      <span class="eyebrow">Scoreline Value</span>
      <h1>比分价值信号</h1>
      <p>
        这里比较模型概率、公平赔率与市场赔率。强价值不是推荐下单，而是提示“模型定价与市场定价差异较大”的研究样本。
      </p>
    </header>

    <DataSnapshotBar />

    <div class="stat-grid">
      <StatCard label="展示样本" :value="String(rows.data.value?.length ?? 0)" hint="当前筛选结果" />
      <StatCard label="强价值数量" :value="String(strongValueRows.length)" hint="market_edge ≥ 10%" />
      <StatCard label="最大市场边际" :value="percent(bestEdge, 2)" hint="模型概率 × 市场赔率 - 1" />
    </div>

    <section class="section-card">
      <div class="toolbar">
        <div>
          <h2>价值比分列表</h2>
          <span>优先展示体彩/市场赔率已接入的比分</span>
        </div>
        <div class="toolbar-controls">
          <ElSelect v-model="activeSignal" placeholder="信号筛选" @change="loadRows">
            <ElOption
              v-for="option in signalOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </ElSelect>
          <ElSelect v-model="sortBy" placeholder="排序" @change="loadRows">
            <ElOption label="按市场边际" value="edge" />
            <ElOption label="按模型概率" value="probability" />
            <ElOption label="按模型排名" value="rank" />
          </ElSelect>
        </div>
      </div>

      <ElAlert
        class="value-note"
        title="价值信号只代表模型与赔率之间的价格差，不代表最终赛果确定性。"
        type="info"
        show-icon
        :closable="false"
      />

      <ElSkeleton v-if="rows.loading.value" :rows="8" animated />
      <ElAlert v-else-if="rows.error.value" :title="rows.error.value" type="error" show-icon />
      <ScorelineTable v-else :rows="rows.data.value ?? []" show-match />
    </section>
  </section>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 18px;
}

.toolbar h2 {
  margin: 0 0 6px;
}

.toolbar span {
  color: var(--color-muted);
}

.toolbar-controls {
  display: flex;
  gap: 12px;
}

.toolbar-controls :deep(.el-select) {
  width: 150px;
}

.value-note {
  margin-bottom: 18px;
}

@media (max-width: 760px) {
  .toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .toolbar-controls {
    flex-direction: column;
  }

  .toolbar-controls :deep(.el-select) {
    width: 100%;
  }
}
</style>
