<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, shallowRef, useTemplateRef, watch } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import * as echarts from 'echarts'

import StatCard from '@/components/common/StatCard.vue'
import { useAsyncState } from '@/composables/useAsyncState'
import { dashboardApi } from '@/services/api'
import type { TeamProfileResponse } from '@/types/api'

const route = useRoute()
const teamName = computed(() => route.params.teamName as string)
const profile = useAsyncState<TeamProfileResponse>()

onMounted(() => {
  profile.run(() => dashboardApi.teamProfile(teamName.value))
})

// Stage chart
const stageChartRef = useTemplateRef<HTMLDivElement>('stageChart')
const stageChart = shallowRef<echarts.ECharts | null>(null)

function stageLabels() {
  const m: Record<string, string> = {
    group_winner: '小组第一', group_runner_up: '小组第二',
    group_advance: '小组出线', round_of_32: '32强',
    round_of_16: '16强', quarter_final: '8强',
    semi_final: '4强', final: '决赛', champion: '冠军',
  }
  return m
}

function buildStageChart(data: TeamProfileResponse) {
  const labels = stageLabels()
  const items = Object.entries(data.stage_probabilities)
    .filter(([k]) => k !== 'simulations')
    .map(([k, v]) => ({ name: labels[k] || k, value: v }))
  return {
    tooltip: { formatter: (p: { name: string; value: number }) => `${p.name}: ${(p.value * 100).toFixed(1)}%` },
    grid: { left: 80, right: 20, top: 10, bottom: 10 },
    xAxis: { type: 'value', max: 1, axisLabel: { formatter: (v: number) => `${(v * 100).toFixed(0)}%`, color: '#8899aa' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } } },
    yAxis: { type: 'category', data: items.map((i) => i.name).reverse(), axisLabel: { color: '#8899aa' } },
    series: [{
      type: 'bar', data: items.reverse().map((i) => ({ value: i.value,
        itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: '#2d756d' }, { offset: 1, color: '#d4a843' }]), borderRadius: [0, 4, 4, 0] },
      })), barWidth: 14,
    }],
  }
}

let _stageInit = false
async function renderStage() {
  await nextTick()
  if (!stageChartRef.value) return
  if (!_stageInit) { stageChart.value = echarts.init(stageChartRef.value); _stageInit = true }
  if (profile.data.value) stageChart.value?.setOption(buildStageChart(profile.data.value), { notMerge: true })
}

watch(profile.data, renderStage)
onMounted(() => { renderStage(); window.addEventListener('resize', renderStage) })
onBeforeUnmount(() => { window.removeEventListener('resize', renderStage); stageChart.value?.dispose() })

// Match label
function matchLabel(m: { home_team_zh: string; away_team_zh: string; is_home: boolean; home_score?: number | null; away_score?: number | null; completed: boolean }) {
  const opp = m.is_home ? m.away_team_zh : m.home_team_zh
  const loc = m.is_home ? 'vs' : '@'
  if (m.completed) {
    const hs = m.home_score ?? 0; const aws = m.away_score ?? 0
    const r = m.is_home ? (hs > aws ? 'W' : hs < aws ? 'L' : 'D') : (aws > hs ? 'W' : aws < hs ? 'L' : 'D')
    return `${r} ${loc} ${opp} ${hs}-${aws}`
  }
  return `○ ${loc} ${opp}`
}
</script>

<template>
  <section class="page-stack">
    <ElAlert v-if="profile.error.value" :title="profile.error.value" type="error" show-icon />
    <div v-if="profile.data.value" class="profile-page">
      <!-- ① Header -->
      <header class="profile-header section-card">
        <div class="header-main">
          <span class="eyebrow">{{ profile.data.value.group_name }} · {{ profile.data.value.confederation }}</span>
          <h1>{{ profile.data.value.team_name_zh }}</h1>
          <div class="header-stats">
            <span>FIFA #{{ profile.data.value.fifa_rank ?? '?' }}</span>
            <span>Elo {{ profile.data.value.elo?.toFixed(0) ?? '?' }}</span>
          </div>
        </div>
        <div class="header-records">
          <StatCard label="积分" :value="String(profile.data.value.points)" />
          <StatCard label="进球" :value="String(profile.data.value.goals_for)" />
          <StatCard label="失球" :value="String(profile.data.value.goals_against)" />
          <StatCard label="净胜球" :value="String(profile.data.value.goal_difference >= 0 ? '+' + profile.data.value.goal_difference : String(profile.data.value.goal_difference))" />
          <StatCard label="出线概率" :value="profile.data.value.group_advance_probability != null ? (profile.data.value.group_advance_probability * 100).toFixed(1) + '%' : '--'" />
        </div>
      </header>

      <!-- ② Recent Form -->
      <section class="section-card">
        <div class="section-title"><h2>近期状态</h2><span>最近 {{ profile.data.value.recent_form.length }} 场</span></div>
        <div class="form-strip">
          <span v-for="(r,i) in [...profile.data.value.recent_form].reverse()" :key="i" class="form-badge" :class="r">{{ r==='W'?'胜':r==='L'?'负':'平' }}</span>
        </div>
      </section>

      <!-- ③ Stage Chart -->
      <section class="section-card">
        <div class="section-title"><h2>晋级之路</h2><span>蒙特卡洛模拟</span></div>
        <div ref="stageChart" style="width:100%;height:280px" />
      </section>

      <!-- ④ Matches -->
      <div class="match-columns">
        <section class="section-card">
          <div class="section-title"><h2>已完赛</h2></div>
          <div v-for="m in profile.data.value.completed_matches" :key="m.match_no" class="match-row">
            <RouterLink :to="`/matches/${m.match_no}`">{{ matchLabel(m) }}</RouterLink>
            <span class="match-date">{{ m.date_et?.slice(0,10) ?? '' }}</span>
          </div>
          <p v-if="!profile.data.value.completed_matches.length" class="muted">暂无</p>
        </section>
        <section class="section-card">
          <div class="section-title"><h2>未开赛</h2></div>
          <div v-for="m in profile.data.value.upcoming_matches" :key="m.match_no" class="match-row">
            <RouterLink :to="`/matches/${m.match_no}`">{{ matchLabel(m) }}</RouterLink>
            <span class="match-date">{{ m.date_et?.slice(0,10) ?? '' }}</span>
          </div>
          <p v-if="!profile.data.value.upcoming_matches.length" class="muted">暂无</p>
        </section>
      </div>

      <!-- ⑤ Squad -->
      <section class="section-card">
        <div class="section-title"><h2>阵容</h2><span>{{ profile.data.value.squad.length }} 人</span></div>
        <ElTable :data="profile.data.value.squad" size="small" class="squad-table">
          <ElTableColumn prop="shirt_no" label="#" width="50" />
          <ElTableColumn label="球员" min-width="110">
            <template #default="{ row }">{{ row.player_name_zh || row.player_name }}</template>
          </ElTableColumn>
          <ElTableColumn prop="position" label="位置" width="70" />
          <ElTableColumn prop="age" label="年龄" width="60" />
          <ElTableColumn prop="goals" label="⚽" width="50" />
          <ElTableColumn prop="assists" label="🅰️" width="50" />
          <ElTableColumn label="牌" width="90">
            <template #default="{ row }">
              <span v-if="row.yellow_cards>0" class="card-badge yellow">🟨{{ row.yellow_cards }}</span>
              <span v-if="row.red_cards>0" class="card-badge red">🟥{{ row.red_cards }}</span>
              <span v-if="!row.yellow_cards && !row.red_cards" class="muted">--</span>
            </template>
          </ElTableColumn>
          <ElTableColumn label="停赛" width="70">
            <template #default="{ row }">
              <ElTag v-if="row.is_suspended" type="danger" size="small">停赛</ElTag>
              <span v-else class="muted">--</span>
            </template>
          </ElTableColumn>
        </ElTable>
      </section>

      <!-- ⑥ Tournament Stats -->
      <section v-if="profile.data.value.tournament_stats.avg_goals_scored != null" class="section-card">
        <div class="section-title"><h2>技术统计</h2><span>本赛季场均</span></div>
        <div class="stat-grid">
          <StatCard label="场均进球" :value="(profile.data.value.tournament_stats.avg_goals_scored ?? 0).toFixed(1)" />
          <StatCard label="场均失球" :value="(profile.data.value.tournament_stats.avg_goals_conceded ?? 0).toFixed(1)" />
          <StatCard label="场均射门" :value="(profile.data.value.tournament_stats.avg_shots ?? 0).toFixed(0)" />
          <StatCard label="场均犯规" :value="(profile.data.value.tournament_stats.avg_fouls ?? 0).toFixed(0)" />
          <StatCard label="场均黄牌" :value="(profile.data.value.tournament_stats.avg_yellow ?? 0).toFixed(1)" />
          <StatCard label="场均红牌" :value="(profile.data.value.tournament_stats.avg_red ?? 0).toFixed(1)" />
        </div>
      </section>
    </div>
  </section>
</template>

<style scoped>
.profile-page { display: grid; gap: 20px; }
.profile-header { display: grid; gap: 20px; }
.header-main { display: grid; gap: 8px; }
.header-main h1 { margin: 0; font-size: clamp(36px,6vw,56px); }
.header-stats { display: flex; gap: 16px; color: var(--color-muted); font-size: 14px; }
.header-records { display: grid; grid-template-columns: repeat(5,minmax(0,1fr)); gap: 12px; }
.form-strip { display: flex; gap: 8px; flex-wrap: wrap; }
.form-badge { width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; border-radius: 8px; font-size: 13px; font-weight: 800; }
.form-badge.W { background: rgba(74,222,128,0.15); color: #4ade80; }
.form-badge.L { background: rgba(248,113,113,0.15); color: #f87171; }
.form-badge.D { background: rgba(212,168,67,0.15); color: #d4a843; }
.match-columns { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 16px; }
.match-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--color-line); }
.match-row a { color: var(--color-ink); text-decoration: none; font-weight: 600; }
.match-date { color: var(--color-muted); font-size: 13px; }
.muted { color: var(--color-muted); }
.card-badge { margin-right: 4px; }
.card-badge.yellow { color: #d4a843; }
.card-badge.red { color: #f87171; }
.squad-table { margin-top: 8px; }
@media (max-width:760px) { .header-records { grid-template-columns: repeat(3,minmax(0,1fr)); } .match-columns { grid-template-columns: 1fr; } }
</style>
