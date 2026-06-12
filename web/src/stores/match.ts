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

  // 返回明天北京日期的所有场次（取今天BJ时间+1天）
  const tomorrowMatches = computed(() => {
    const now = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Shanghai' }))
    const tomorrow = new Date(now)
    tomorrow.setDate(now.getDate() + 1)
    const y = tomorrow.getFullYear()
    const m = String(tomorrow.getMonth() + 1).padStart(2, '0')
    const d = String(tomorrow.getDate()).padStart(2, '0')
    const tomorrowStr = `${y}-${m}-${d}`
    return matches.value.filter((match) => match.date_bj === tomorrowStr)
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
    tomorrowMatches,
    loading,
    error,
    loadMatches,
  }
})
