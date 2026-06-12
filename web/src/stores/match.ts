import { defineStore } from 'pinia'
import { computed, shallowRef } from 'vue'

import { dashboardApi } from '@/services/api'
import type { MatchSummary } from '@/types/api'

export const useMatchStore = defineStore('match', () => {
  const matches = shallowRef<MatchSummary[]>([])
  const loading = shallowRef(false)
  const error = shallowRef<string | null>(null)

  const recentCompletedMatches = computed(() => {
    return matches.value.filter((match) => match.completed).slice(-4).reverse()
  })

  const firstFourMatches = computed(() => {
    const upcoming = matches.value.filter((match) => !match.completed)
    if (upcoming.length >= 4) {
      return upcoming.slice(0, 4)
    }

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
    recentCompletedMatches,
    firstFourMatches,
    loading,
    error,
    loadMatches,
  }
})
