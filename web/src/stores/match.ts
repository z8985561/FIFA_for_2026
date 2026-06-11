import { defineStore } from 'pinia'
import { computed, shallowRef } from 'vue'

import { dashboardApi } from '@/services/api'
import type { MatchSummary } from '@/types/api'

export const useMatchStore = defineStore('match', () => {
  const matches = shallowRef<MatchSummary[]>([])
  const loading = shallowRef(false)
  const error = shallowRef<string | null>(null)

  const firstFourMatches = computed(() => matches.value.slice(0, 4))

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
