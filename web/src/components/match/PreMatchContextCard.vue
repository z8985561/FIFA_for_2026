<script setup lang="ts">
import type { MatchPreviewSource } from '@/types/api'

const props = defineProps<{
  sources: readonly MatchPreviewSource[]
}>()

function openUrl(url?: string | null) {
  if (url) window.open(url, '_blank', 'noopener')
}

function hasContent(source: MatchPreviewSource): boolean {
  return !!(
    source.predicted_lineup_text ||
    source.injury_notes ||
    source.coach_quotes ||
    source.key_player_notes
  )
}
</script>

<template>
  <section v-if="props.sources.length" class="section-card">
    <div class="section-title">
      <h2>赛前情报</h2>
      <span>{{ props.sources.length }} 个来源</span>
    </div>

    <ElCollapse accordion>
      <ElCollapseItem
        v-for="(source, i) in props.sources"
        :key="i"
      >
        <template #title>
          <div class="source-header">
            <span class="source-name">{{ source.source_name || '未知来源' }}</span>
            <span v-if="source.published_time" class="source-time">{{ source.published_time }}</span>
            <ElTag
              v-if="source.source_url"
              size="small"
              type="info"
              class="source-link-tag"
              @click.stop="openUrl(source.source_url)"
            >
              查看原文
            </ElTag>
          </div>
        </template>

        <div v-if="hasContent(source)" class="source-body">
          <div v-if="source.predicted_lineup_text" class="source-block">
            <h4>预测首发</h4>
            <pre>{{ source.predicted_lineup_text }}</pre>
          </div>
          <div v-if="source.injury_notes" class="source-block">
            <h4>伤病 / 停赛</h4>
            <pre>{{ source.injury_notes }}</pre>
          </div>
          <div v-if="source.coach_quotes" class="source-block">
            <h4>教练发言</h4>
            <pre>{{ source.coach_quotes }}</pre>
          </div>
          <div v-if="source.key_player_notes" class="source-block">
            <h4>关键球员</h4>
            <pre>{{ source.key_player_notes }}</pre>
          </div>
        </div>
        <div v-else class="source-body muted">暂无详细内容</div>
      </ElCollapseItem>
    </ElCollapse>
  </section>
</template>

<style scoped>
.source-header {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.source-name {
  font-weight: 700;
}

.source-time {
  color: var(--color-muted);
  font-size: 13px;
}

.source-link-tag {
  cursor: pointer;
}

.source-body {
  display: grid;
  gap: 18px;
  padding: 8px 0;
}

.source-block h4 {
  margin: 0 0 6px;
  font-size: 14px;
  color: var(--color-accent);
}

.source-block pre {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--color-ink);
}

.muted {
  color: var(--color-muted);
  font-size: 13px;
}
</style>
