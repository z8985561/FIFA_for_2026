<script setup lang="ts">
import { computed } from 'vue'

import type { MatchDetail, TeamContext, TeamCompareItem } from '@/types/api'

const props = defineProps<{
  detail: MatchDetail | { match: any; home_team_context?: any; away_team_context?: any }
  homeCompare?: TeamCompareItem | null
  awayCompare?: TeamCompareItem | null
}>()

function teamSummary(side: 'home' | 'away'): string {
  const ctx: TeamContext | null | undefined = side === 'home' ? props.detail.home_team_context : props.detail.away_team_context
  const cmp = side === 'home' ? props.homeCompare : props.awayCompare
  const name = side === 'home' ? props.detail.match.home_team_zh : props.detail.match.away_team_zh
  if (!cmp) return `${name}数据暂不可用。`

  const parts: string[] = []

  // Elo and rank
  parts.push(`${name}目前 FIFA 排名第${cmp.fifa_rank ?? '?'}位，Elo 评分 ${cmp.elo?.toFixed(0) ?? '?'}，属于${cmp.fifa_rank && cmp.fifa_rank <= 10 ? '世界顶级' : cmp.fifa_rank && cmp.fifa_rank <= 30 ? '中上游' : '中游'}球队。`)

  // Squad
  parts.push(`球队阵容${cmp.squad_size ?? 26}人，平均年龄${cmp.average_age?.toFixed(1) ?? '?'}岁，全队累计国际比赛出场${cmp.total_caps ?? '?'}次，${(cmp.average_age ?? 27) < 26 ? '阵容年轻有活力' : (cmp.average_age ?? 27) > 29 ? '经验丰富但年龄偏大' : '年龄结构均衡'}。`)

  // Group position
  if (cmp.group_advance_probability != null) {
    const prob = cmp.group_advance_probability
    if (prob > 0.8) parts.push(`小组出线形势乐观，模型给出 ${(prob * 100).toFixed(0)}% 的出线概率。`)
    else if (prob > 0.4) parts.push(`小组出线形势胶着，当前出线概率约 ${(prob * 100).toFixed(0)}%，仍需全力争胜。`)
    else parts.push(`小组出线形势严峻，出线概率仅 ${(prob * 100).toFixed(0)}%，剩余每场比赛都至关重要。`)
  }

  // Tournament stats
  if (cmp.avg_goals_scored != null) {
    parts.push(`本届赛事场均进球${cmp.avg_goals_scored.toFixed(1)}、失球${cmp.avg_goals_conceded?.toFixed(1)}，场均射门${cmp.avg_shots?.toFixed(0)}次。`)
  }

  // Suspensions and coach
  if (ctx) {
    if (ctx.suspended_count > 0) {
      parts.push(`⚠️ 球队当前有 ${ctx.suspended_count} 名球员停赛：${ctx.suspended_players_zh.join('、')}，对阵容深度构成影响。`)
    }
    if (ctx.coach_name_zh) {
      parts.push(`主教练${ctx.coach_name_zh}执教。`)
    }
  }

  return parts.join('')
}

const homeText = computed(() => teamSummary('home'))
const awayText = computed(() => teamSummary('away'))
</script>

<template>
  <section class="section-card">
    <div class="section-title">
      <h2>球队分析</h2>
      <span>数据驱动的综合评估</span>
    </div>
    <div class="summary-grid">
      <div class="summary-block">
        <h3>{{ detail.match.home_team_zh }}</h3>
        <p>{{ homeText }}</p>
      </div>
      <div class="summary-block">
        <h3>{{ detail.match.away_team_zh }}</h3>
        <p>{{ awayText }}</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.summary-block h3 {
  margin: 0 0 10px;
  font-size: 18px;
  color: var(--color-accent);
}

.summary-block p {
  margin: 0;
  line-height: 1.8;
  color: var(--color-ink);
}

@media (max-width: 760px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
