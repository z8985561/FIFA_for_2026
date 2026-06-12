<script setup lang="ts">
import { computed, onMounted, shallowRef } from 'vue'

import DataCompletenessBadge from '@/components/common/DataCompletenessBadge.vue'
import DataSnapshotBar from '@/components/common/DataSnapshotBar.vue'
import StatCard from '@/components/common/StatCard.vue'
import { useAsyncState } from '@/composables/useAsyncState'
import { dashboardApi } from '@/services/api'
import type { DataQualityRow, ScheduleMatch } from '@/types/api'

const schedule = useAsyncState<ScheduleMatch[]>()
const dataQuality = useAsyncState<DataQualityRow[]>()
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

interface ScheduleDayGroup {
  date: string
  title: string
  matches: ScheduleMatch[]
}

const rows = computed(() => schedule.data.value ?? [])

const qualityByMatch = computed(() => {
  return new Map((dataQuality.data.value ?? []).map((row) => [row.match_no, row]))
})

const stageOptions = computed(() => {
  return [...new Set(rows.value.map((row) => row.stage))]
})

const groupOptions = computed(() => {
  return [...new Set(rows.value.map((row) => row.group_name).filter(Boolean))] as string[]
})

const groupedRows = computed<ScheduleDayGroup[]>(() => {
  const groups = new Map<string, ScheduleMatch[]>()
  for (const row of rows.value) {
    const date = row.date_bj ?? 'date-pending'
    const matches = groups.get(date) ?? []
    matches.push(row)
    groups.set(date, matches)
  }

  return [...groups.entries()].map(([date, matches]) => ({
    date,
    title: formatDateTitle(date, matches.length),
    matches,
  }))
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

function qualityFor(matchNo: number) {
  return qualityByMatch.value.get(matchNo)
}

function formatDateTitle(date: string, count: number) {
  if (date === 'date-pending') {
    return `日期待定 · ${count}场`
  }
  const parsed = new Date(`${date}T00:00:00+08:00`)
  const label = new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'short',
  }).format(parsed)
  return `${label} · ${count}场`
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

onMounted(() => {
  loadSchedule()
  dataQuality.run(dashboardApi.dataQuality)
})
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
      <ElAlert
        v-else-if="schedule.error.value"
        :title="schedule.error.value"
        type="error"
        show-icon
      />
      <ElEmpty v-else-if="!groupedRows.length" description="当前筛选条件下暂无赛程" />
      <div v-else class="schedule-days">
        <article v-for="group in groupedRows" :key="group.date" class="schedule-day">
          <header class="day-header">
            <h3>{{ group.title }}</h3>
          </header>

          <div class="match-list">
            <article v-for="match in group.matches" :key="match.match_no" class="schedule-match">
              <div class="match-time">
                <span>第 {{ match.match_no }} 场</span>
                <strong>{{ match.time_bj }}</strong>
              </div>

              <div class="match-main">
                <div class="match-tags">
                  <ElTag effect="plain">{{ stageText(match.stage) }}</ElTag>
                  <ElTag v-if="match.group_name" type="info" effect="plain">
                    {{ match.group_name }}
                  </ElTag>
                  <DataCompletenessBadge
                    :level="qualityFor(match.match_no)?.completeness_level"
                    :score="qualityFor(match.match_no)?.completeness_score"
                    :missing-items="qualityFor(match.match_no)?.missing_items ?? []"
                  />
                </div>

                <h4>
                  {{ match.home_team_zh }}
                  <span>vs</span>
                  {{ match.away_team_zh }}
                </h4>
                <p>{{ match.venue_city }}</p>
              </div>

              <div class="match-side">
                <div v-if="match.completed" class="score-result">
                  <strong>{{ match.actual_home_score }} - {{ match.actual_away_score }}</strong>
                  <span class="muted">已完赛</span>
                </div>

                <RouterLink
                  v-if="match.stage === 'Group Stage' && match.match_no <= 72"
                  :to="`/matches/${match.match_no}`"
                  class="analysis-link"
                >
                  查看分析
                </RouterLink>
                <span v-else-if="!match.completed" class="muted">对阵待定</span>
              </div>
            </article>
          </div>
        </article>
      </div>
    </section>
  </section>
</template>

<style scoped>
.schedule-toolbar {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 22px;
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

.schedule-days {
  display: grid;
  gap: 22px;
}

.schedule-day {
  display: grid;
  gap: 12px;
}

.day-header {
  padding: 12px 16px;
  border-radius: var(--radius-lg);
  background: rgba(23, 40, 45, 0.08);
}

.day-header h3 {
  margin: 0;
  font-size: 18px;
}

.match-list {
  display: grid;
  gap: 12px;
}

.schedule-match {
  display: grid;
  grid-template-columns: 120px 1fr 110px;
  gap: 18px;
  align-items: center;
  padding: 18px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.62);
}

.match-time {
  display: grid;
  gap: 6px;
}

.match-time span,
.match-main p,
.match-main h4 span {
  color: var(--color-muted);
}

.match-time strong {
  font-size: 26px;
}

.match-main {
  display: grid;
  gap: 8px;
}

.match-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.match-main h4 {
  margin: 0;
  font-size: 22px;
}

.match-main h4 span {
  margin: 0 10px;
  font-size: 15px;
}

.match-main p {
  margin: 0;
}

.match-side {
  display: grid;
  justify-items: end;
  gap: 10px;
}

.score-result {
  display: grid;
  justify-items: end;
  gap: 4px;
}

.score-result strong {
  font-size: 28px;
  line-height: 1;
}

.analysis-link {
  color: var(--color-danger);
  font-weight: 800;
  text-decoration: none;
}

@media (max-width: 900px) {
  .schedule-match {
    grid-template-columns: 1fr;
  }

  .match-side,
  .analysis-link,
  .score-result {
    justify-self: start;
    justify-items: start;
  }
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
