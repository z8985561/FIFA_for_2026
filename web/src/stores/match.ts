import { defineStore } from 'pinia'
import { computed, shallowRef } from 'vue'

import { dashboardApi } from '@/services/api'
import type { MatchSummary } from '@/types/api'

export const useMatchStore = defineStore('match', () => {
  const matches = shallowRef<MatchSummary[]>([])
  const loading = shallowRef(false)
  const error = shallowRef<string | null>(null)

  const firstFourMatches = computed(() => {
    const upcoming = matches.value.filter((match) => !match.completed)
    // 优先展示尚未结束的最新四场。
    if (upcoming.length >= 4) {
      return upcoming.slice(0, 4)
    }
    // 未结束的不足四场时（赛事接近尾声），用最近已结束的比赛按时间顺序补齐，避免首页空缺。
    const finished = matches.value.filter((match) => match.completed)
    const fill = finished.slice(-(4 - upcoming.length))
    return [...fill, ...upcoming]
  })

  async function loadMatches() {
    loading.value = true
    error.value = null
    try {
      matches.value = await dashboardApi.matches()
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '比赛列表加载失败'
    } finally {
      loading.value = false
    }
  }

  return {
    matches,
    firstFourMatches,
    loading,
    error,
    loadMatches,
  }
})
