<script setup lang="ts">
const props = defineProps<{
  level?: 'High' | 'Medium' | 'Low'
  score?: number
  missingItems?: readonly string[]
}>()

const levelMap = {
  High: {
    label: 'High',
    type: 'success',
    detail: '核心数据较完整',
  },
  Medium: {
    label: 'Medium',
    type: 'warning',
    detail: '已有基础数据，部分细节待补充',
  },
  Low: {
    label: 'Low',
    type: 'info',
    detail: '当前仅具备有限数据',
  },
} as const

const missingLabels: Record<string, string> = {
  missing_prediction: '缺胜平负预测',
  missing_scoreline_model: '缺比分模型',
  missing_score_odds: '缺比分赔率',
  missing_market_odds: '缺市场赔率',
  missing_lineup_adjustment: '缺阵容修正',
  missing_snapshot_time: '缺快照时间',
}

function missingText() {
  const items = props.missingItems ?? []
  if (!items.length) {
    return '核心数据已接入'
  }
  return items.map((item) => missingLabels[item] ?? item).join('、')
}
</script>

<template>
  <ElTooltip
    :content="`${levelMap[level ?? 'Low'].detail}；${missingText()}`"
    placement="top"
  >
    <ElTag :type="levelMap[level ?? 'Low'].type" effect="plain" round>
      {{ levelMap[level ?? 'Low'].label }} · {{ score ?? 0 }}
    </ElTag>
  </ElTooltip>
</template>
