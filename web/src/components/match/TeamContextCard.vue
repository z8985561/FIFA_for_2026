<script setup lang="ts">
import type { TeamContext } from '@/types/api'

const props = defineProps<{
  context: TeamContext | null | undefined
  side: 'home' | 'away'
}>()
</script>

<template>
  <div class="team-context-card">
    <div class="tc-head">
      <ElTag :type="props.side === 'home' ? 'primary' : 'warning'" size="small">
        {{ props.side === 'home' ? '主队' : '客队' }}
      </ElTag>
      <strong>{{ props.context?.team_name_zh || '暂无数据' }}</strong>
    </div>

    <template v-if="props.context">
      <div class="tc-row">
        <span>教练</span>
        <strong>{{ props.context.coach_name_zh || props.context.coach_name_en || '暂无' }}</strong>
      </div>
      <div class="tc-row">
        <span>阵容人数</span>
        <strong>{{ props.context.squad_size ?? '暂无' }}</strong>
      </div>
      <div class="tc-row">
        <span>停赛球员</span>
        <div v-if="props.context.suspended_count > 0" class="tc-tags">
          <ElTag
            v-for="(name, i) in props.context.suspended_players_zh"
            :key="i"
            type="danger"
            size="small"
          >
            {{ name }}
          </ElTag>
        </div>
        <span v-else class="muted">无停赛球员</span>
      </div>
    </template>
    <div v-else class="tc-row muted">暂无球队数据</div>
  </div>
</template>

<style scoped>
.team-context-card {
  display: grid;
  gap: 12px;
  padding: 18px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
  background: rgba(18, 35, 64, 0.5);
}

.tc-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.tc-head strong {
  font-size: 18px;
}

.tc-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.tc-row span {
  color: var(--color-muted);
  font-size: 13px;
}

.tc-row strong {
  font-size: 15px;
}

.tc-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.muted {
  color: var(--color-muted);
  font-size: 13px;
}
</style>
