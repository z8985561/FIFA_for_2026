<script setup lang="ts">
import { computed, onMounted, shallowRef } from 'vue'

import DataSnapshotBar from '@/components/common/DataSnapshotBar.vue'
import StatCard from '@/components/common/StatCard.vue'
import { useAsyncState } from '@/composables/useAsyncState'
import { dashboardApi } from '@/services/api'
import type { ScheduleMatch } from '@/types/api'

const schedule = useAsyncState<ScheduleMatch[]>()
const activeStage = shallowRef('')
const activeGroup = shallowRef('')

const stageLabels: Record<string, string> = {
  'Group Stage': '小组赛',
  'Round of 32': '32 强',
  'Round of 16': '16 强',
  'Quarter-Finals': '1/4 决赛',
  'Semi-Finals': '半决赛',
  'Third Place': '三四名决赛',
  Final: '决赛',
}

const rows = computed(() => schedule.data.value ?? [])

const stageOptions = computed(() => {
  return [...new Set(rows.value.map((row) => row.stage))]
})

const groupOptions = computed(() => {
  return [...new Set(rows.value.map((row) => row.group_name).filter(Boolean))] as string[]
})

const groupStageCount = computed(() => {
  return rows.value.filter((row) => row.stage === 'Group Stage').length
})

const knockoutCount = computed(() => {
  return rows.value.filter((row) => row.stage !== 'Group Stage').length
})

const firstKickoffBj = computed(() => {
  const first = rows.value[0]
  return first ? `${first.date_bj} ${first.time_bj}` : '暂无'
})

function stageText(stage: string) {
  return stageLabels[stage] ?? stage
}

function loadSchedule() {
  schedule.run(() =>
    dashboardApi.schedule({
      stage: activeStage.value || undefined,
      groupName: activeGroup.value || undefined,
    }),
  )
}

function resetFilters() {
  activeStage.value = ''
  activeGroup.value = ''
  loadSchedule()
}

onMounted(loadSchedule)
</script>

<template>
  <section class="page-stack">
    <header class="page-heading">
      <span class="eyebrow">Official Schedule</span>
      <h1>2026 世界杯完整赛程</h1>
      <p>
        覆盖 104 场比赛，包含小组赛、32 强、16 强、1/4 决赛、半决赛、三四名决赛和决赛。淘汰赛对阵未产生前显示为待定。
      </p>
    </header>

    <DataSnapshotBar />

    <div class="stat-grid">
      <StatCard label="总场次" :value="String(rows.length)" hint="完整官方赛程" />
      <StatCard label="小组赛" :value="String(groupStageCount)" hint="12 组，每组 6 场" />
      <StatCard label="淘汰赛" :value="String(knockoutCount)" hint="含三四名与决赛" />
    </div>

    <section class="section-card">
      <div class="schedule-toolbar">
        <div>
          <h2>赛程列表</h2>
          <span>首场北京时间：{{ firstKickoffBj }}</span>
        </div>
        <div class="schedule-controls">
          <ElSelect v-model="activeStage" placeholder="阶段" clearable @change="loadSchedule">
            <ElOption
              v-for="stage in stageOptions"
              :key="stage"
              :label="stageText(stage)"
              :value="stage"
            />
          </ElSelect>
          <ElSelect v-model="activeGroup" placeholder="小组" clearable @change="loadSchedule">
            <ElOption
              v-for="group in groupOptions"
              :key="group"
              :label="group"
              :value="group"
            />
          </ElSelect>
          <ElButton @click="resetFilters">重置</ElButton>
        </div>
      </div>

      <ElSkeleton v-if="schedule.loading.value" :rows="10" animated />
      <ElAlert v-else-if="schedule.error.value" :title="schedule.error.value" type="error" show-icon />
      <ElTable v-else :data="rows" class="schedule-table">
        <ElTableColumn prop="match_no" label="场次" width="80" fixed />
        <ElTableColumn label="阶段" min-width="120">
          <template #default="{ row }">{{ stageText(row.stage) }}</template>
        </ElTableColumn>
        <ElTableColumn prop="group_name" label="小组" width="110" />
        <ElTableColumn label="北京时间" min-width="150">
          <template #default="{ row }">{{ row.date_bj }} {{ row.time_bj }}</template>
        </ElTableColumn>
        <ElTableColumn label="对阵" min-width="220">
          <template #default="{ row }">
            <strong>{{ row.home_team_zh }}</strong>
            <span class="versus">vs</span>
            <strong>{{ row.away_team_zh }}</strong>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="venue_city" label="场馆 / 城市" min-width="260" />
        <ElTableColumn label="分析" width="100">
          <template #default="{ row }">
            <RouterLink
              v-if="row.stage === 'Group Stage' && row.match_no <= 72"
              :to="`/matches/${row.match_no}`"
            >
              查看
            </RouterLink>
            <span v-else class="muted">待定</span>
          </template>
        </ElTableColumn>
      </ElTable>
    </section>
  </section>
</template>

<style scoped>
.schedule-toolbar {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 18px;
}

.schedule-toolbar h2 {
  margin: 0 0 6px;
}

.schedule-toolbar span,
.muted {
  color: var(--color-muted);
}

.schedule-controls {
  display: flex;
  gap: 12px;
}

.schedule-controls :deep(.el-select) {
  width: 150px;
}

.schedule-table {
  width: 100%;
  border-radius: var(--radius-md);
  overflow: hidden;
}

.versus {
  margin: 0 10px;
  color: var(--color-muted);
}

@media (max-width: 760px) {
  .schedule-toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .schedule-controls {
    flex-direction: column;
  }

  .schedule-controls :deep(.el-select) {
    width: 100%;
  }
}
</style>
