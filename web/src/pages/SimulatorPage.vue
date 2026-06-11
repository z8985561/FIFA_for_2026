<script setup lang="ts">
import { computed, onMounted, reactive, shallowRef, watch } from 'vue'

import DataSnapshotBar from '@/components/common/DataSnapshotBar.vue'
import ScorelineTable from '@/components/match/ScorelineTable.vue'
import { useAsyncState } from '@/composables/useAsyncState'
import { dashboardApi } from '@/services/api'
import type { ScorelineRow, SimulatorResponse, SimulatorSelection } from '@/types/api'

const candidates = useAsyncState<ScorelineRow[]>()
const result = shallowRef<SimulatorResponse | null>(null)
const calculating = shallowRef(false)
const form = reactive({
  budget: 50,
  stake_per_combination: 2,
  bet_type: '4x1',
  selectedKeys: [] as string[],
})

const selectedRows = computed(() => {
  const keySet = new Set(form.selectedKeys)
  return (candidates.data.value ?? []).filter((row) => keySet.has(rowKey(row)))
})

function rowKey(row: ScorelineRow) {
  return `${row.match_no}:${row.scoreline}`
}

function toSelection(row: ScorelineRow): SimulatorSelection {
  return {
    match_no: row.match_no,
    scoreline: row.scoreline,
  }
}

function percent(value?: number | null) {
  return value == null ? '暂无' : `${(value * 100).toFixed(3)}%`
}

function money(value?: number | null) {
  return value == null ? '暂无' : `${value.toFixed(2)} 元`
}

async function settle() {
  if (!selectedRows.value.length) {
    result.value = null
    return
  }
  calculating.value = true
  try {
    result.value = await dashboardApi.settleSimulator({
      budget: form.budget,
      stake_per_combination: form.stake_per_combination,
      bet_type: form.bet_type,
      selections: selectedRows.value.map(toSelection),
    })
  } finally {
    calculating.value = false
  }
}

let timer: number | undefined
watch(
  () => [form.budget, form.stake_per_combination, form.bet_type, ...form.selectedKeys],
  () => {
    window.clearTimeout(timer)
    timer = window.setTimeout(settle, 350)
  },
)

onMounted(() => {
  candidates.run(() => dashboardApi.valueScorelines(20, 'probability'))
})
</script>

<template>
  <section class="page-stack">
    <header class="page-heading">
      <span class="eyebrow">Mock Simulator</span>
      <h1>虚拟组合模拟器</h1>
      <p>只做概率、理论返奖和风险分层研究，不构成购彩建议。</p>
    </header>

    <DataSnapshotBar />

    <section class="section-card simulator-layout">
      <div class="sim-form">
        <ElForm label-position="top">
          <ElFormItem label="预算">
            <ElInputNumber v-model="form.budget" :min="2" :step="2" />
          </ElFormItem>
          <ElFormItem label="每组合金额">
            <ElInputNumber v-model="form.stake_per_combination" :min="2" :step="2" />
          </ElFormItem>
          <ElFormItem label="串关类型">
            <ElSelect v-model="form.bet_type">
              <ElOption label="单关" value="single" />
              <ElOption label="2 串 1" value="2x1" />
              <ElOption label="4 串 1" value="4x1" />
            </ElSelect>
          </ElFormItem>
        </ElForm>

        <ElAlert
          title="模拟器不会生成真实订单，也不会跳转任何购买页面。"
          type="warning"
          show-icon
          :closable="false"
        />
      </div>

      <div class="sim-result">
        <ElSkeleton v-if="calculating" :rows="5" animated />
        <template v-else-if="result">
          <div class="risk-score">
            <span>风险评级</span>
            <strong>{{ result.risk_rating }}</strong>
            <small>风险分 {{ result.risk_score }}</small>
          </div>
          <div class="result-grid">
            <span>组合数：{{ result.combination_count }}</span>
            <span>总投入：{{ money(result.total_stake) }}</span>
            <span>最大返奖：{{ money(result.max_theoretical_payout) }}</span>
            <span>命中概率：{{ percent(result.estimated_hit_probability) }}</span>
            <span>期望净收益：{{ money(result.expected_net_return) }}</span>
          </div>
          <ul class="risk-reasons">
            <li v-for="reason in result.risk_reasons" :key="reason">{{ reason }}</li>
          </ul>
        </template>
        <ElEmpty v-else description="请选择比分组合后查看模拟结果" />
      </div>
    </section>

    <section class="section-card">
      <div class="section-title">
        <h2>选择比分</h2>
        <span>按模型概率优先展示</span>
      </div>
      <div class="pick-grid">
        <ElCheckboxGroup v-model="form.selectedKeys">
          <ElCheckbox
            v-for="row in candidates.data.value ?? []"
            :key="rowKey(row)"
            :label="rowKey(row)"
            border
          >
            第 {{ row.match_no }} 场 {{ row.scoreline }} · {{ percent(row.model_probability) }}
          </ElCheckbox>
        </ElCheckboxGroup>
      </div>
      <ScorelineTable :rows="selectedRows" />
    </section>
  </section>
</template>

<style scoped>
.simulator-layout {
  display: grid;
  grid-template-columns: minmax(240px, 320px) 1fr;
  gap: 24px;
}

.sim-form,
.sim-result {
  padding: 20px;
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.62);
}

.risk-score {
  display: grid;
  gap: 6px;
}

.risk-score strong {
  font-size: 42px;
  color: var(--color-danger);
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 18px 0;
}

.risk-reasons {
  margin: 0;
  padding-left: 18px;
  color: var(--color-muted);
}

.pick-grid :deep(.el-checkbox-group) {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 20px;
}

@media (max-width: 900px) {
  .simulator-layout {
    grid-template-columns: 1fr;
  }
}
</style>
