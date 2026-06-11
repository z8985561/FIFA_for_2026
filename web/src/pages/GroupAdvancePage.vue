<script setup lang="ts">
import { computed, onMounted, shallowRef } from 'vue'

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
        2026 赛制为 12 个小组，每组前两名直接晋级，另取 8 支成绩最好的小组第三。
      </p>
    </header>

    <ElTabs v-model="activeGroup" class="group-tabs">
      <ElTabPane v-for="group in groups" :key="group" :label="group" :name="group" />
    </ElTabs>

    <section class="section-card">
      <ElTable :data="visibleRows">
        <ElTableColumn prop="team_name_zh" label="球队" min-width="140" />
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
