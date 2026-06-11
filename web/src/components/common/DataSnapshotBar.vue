<script setup lang="ts">
import { computed, onMounted } from 'vue'

import { useAsyncState } from '@/composables/useAsyncState'
import { dashboardApi } from '@/services/api'
import type { MetadataResponse } from '@/types/api'

const metadata = useAsyncState<MetadataResponse>()

const scoreOddsTime = computed(() => {
  const value = metadata.data.value?.latest_score_odds_fetched_at
  if (!value) {
    return '暂无赔率快照'
  }
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
})

const rowSummary = computed(() => {
  const rows = metadata.data.value?.row_counts
  if (!rows) {
    return '数据加载中'
  }
  return `比赛 ${rows.enhanced_predictions ?? 0} · 比分 ${rows.scorelines ?? 0} · 价值 ${rows.value_bets ?? 0}`
})

onMounted(() => {
  metadata.run(dashboardApi.metadata)
})
</script>

<template>
  <aside class="snapshot-bar">
    <div>
      <span class="snapshot-label">数据快照</span>
      <strong>{{ scoreOddsTime }}</strong>
    </div>
    <div>
      <span class="snapshot-label">模型版本</span>
      <strong>{{ metadata.data.value?.model_version ?? '加载中' }}</strong>
    </div>
    <div>
      <span class="snapshot-label">数据规模</span>
      <strong>{{ rowSummary }}</strong>
    </div>
    <p>{{ metadata.data.value?.compliance_note ?? '仅用于概率研究和虚拟模拟。' }}</p>
  </aside>
</template>

<style scoped>
.snapshot-bar {
  display: grid;
  grid-template-columns: 1.1fr 0.9fr 1fr 1.6fr;
  gap: 16px;
  align-items: center;
  padding: 16px 18px;
  border: 1px solid rgba(45, 117, 109, 0.22);
  border-radius: var(--radius-lg);
  background:
    linear-gradient(135deg, rgba(45, 117, 109, 0.12), rgba(223, 180, 102, 0.12)),
    rgba(255, 250, 240, 0.68);
  box-shadow: var(--shadow-soft);
}

.snapshot-label {
  display: block;
  margin-bottom: 4px;
  color: var(--color-muted);
  font-size: 12px;
}

.snapshot-bar strong {
  font-size: 14px;
}

.snapshot-bar p {
  margin: 0;
  color: var(--color-muted);
  line-height: 1.6;
}

@media (max-width: 1000px) {
  .snapshot-bar {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .snapshot-bar {
    grid-template-columns: 1fr;
  }
}
</style>
