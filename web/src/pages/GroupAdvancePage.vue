<script setup lang="ts">
import { computed, onMounted, shallowRef } from 'vue'

import StatCard from '@/components/common/StatCard.vue'
import { useAsyncState } from '@/composables/useAsyncState'
import { dashboardApi } from '@/services/api'
import type { GroupAdvanceRow } from '@/types/api'

const groupRows = useAsyncState<GroupAdvanceRow[]>()
const activeGroup = shallowRef('Group A')

const groups = computed(() => {
  const names = new Set((groupRows.data.value ?? []).map((row) => row.group_name))
  return [...names]
})

const visibleRows = computed(() => {
  return (groupRows.data.value ?? []).filter((row) => row.group_name === activeGroup.value)
})

const completedMatches = computed(() => {
  const totalPlayed = visibleRows.value.reduce((sum, row) => sum + row.played, 0)
  return totalPlayed / 2
})

const liveLeader = computed(() => visibleRows.value[0]?.team_name_zh ?? '暂无')

function percent(value: number) {
  return `${(value * 100).toFixed(1)}%`
}

onMounted(() => {
  groupRows.run(dashboardApi.groupAdvance)
})
</script>

<template>
  <section class="page-stack">
    <header class="page-heading">
      <span class="eyebrow">Group Advance</span>
      <h1>小组出线概率</h1>
      <p>
        2026 赛制共有 12 个小组，每组前两名直接晋级，另外取 8 支成绩最好的小组第三名。
      </p>
    </header>

    <div class="stat-grid">
      <StatCard label="当前小组" :value="activeGroup" hint="真实积分与模型概率并排查看" />
      <StatCard label="已完成场次" :value="String(completedMatches)" hint="按官方已完赛结果统计" />
      <StatCard label="当前榜首" :value="liveLeader" hint="积分相同按净胜球与进球数排序" />
    </div>

    <ElTabs v-model="activeGroup" class="group-tabs">
      <ElTabPane v-for="group in groups" :key="group" :label="group" :name="group" />
    </ElTabs>

    <section class="section-card">
      <p class="table-note">左侧是真实积分表，右侧是模型给出的出线概率。</p>
      <ElTable :data="visibleRows">
        <ElTableColumn prop="standing_rank" label="排名" width="72" />
        <ElTableColumn prop="team_name_zh" label="球队" min-width="140" />
        <ElTableColumn prop="points" label="积分" width="80" />
        <ElTableColumn prop="goal_difference" label="净胜球" width="90" />
        <ElTableColumn prop="played" label="已赛" width="80" />
        <ElTableColumn label="小组第一">
          <template #default="{ row }">{{ percent(row.group_winner_probability) }}</template>
        </ElTableColumn>
        <ElTableColumn label="前二">
          <template #default="{ row }">{{ percent(row.top2_probability) }}</template>
        </ElTableColumn>
        <ElTableColumn label="第三晋级">
          <template #header>
            <ElTooltip content="第三名晋级概率来自跨组横向比较，而不是单一小组内排序。">
              <span>第三晋级</span>
            </ElTooltip>
          </template>
          <template #default="{ row }">
            {{ percent(row.third_place_advance_probability) }}
          </template>
        </ElTableColumn>
        <ElTableColumn label="总晋级">
          <template #default="{ row }">{{ percent(row.group_advance_probability) }}</template>
        </ElTableColumn>
      </ElTable>
    </section>
  </section>
</template>

<style scoped>
.table-note {
  margin: 0 0 16px;
  color: var(--color-muted);
}
</style>
