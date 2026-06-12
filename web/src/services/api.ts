import type {
  DataQualityRow,
  GroupAdvanceRow,
  HealthResponse,
  MatchDetail,
  MatchReviewRow,
  MatchSummary,
  MetadataResponse,
  ScheduleMatch,
  ScorelineRow,
  SimulatorResponse,
  SimulatorSelection,
} from '@/types/api'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  })

  if (!response.ok) {
    throw new Error(`API 请求失败：${response.status}`)
  }

  return (await response.json()) as T
}

export const dashboardApi = {
  health: () => request<HealthResponse>('/api/health'),
  metadata: () => request<MetadataResponse>('/api/metadata'),
  schedule: (params?: { stage?: string; groupName?: string }) => {
    const query = new URLSearchParams()
    if (params?.stage) {
      query.set('stage', params.stage)
    }
    if (params?.groupName) {
      query.set('group_name', params.groupName)
    }
    const suffix = query.toString() ? `?${query.toString()}` : ''
    return request<ScheduleMatch[]>(`/api/schedule${suffix}`)
  },
  dataQuality: () => request<DataQualityRow[]>('/api/data-quality'),
  matches: (limit?: number) => {
    const query = limit ? `?limit=${limit}` : ''
    return request<MatchSummary[]>(`/api/matches${query}`)
  },
  matchDetail: (matchNo: number) => request<MatchDetail>(`/api/matches/${matchNo}`),
  matchScorelines: (matchNo: number, limit = 10) =>
    request<ScorelineRow[]>(`/api/matches/${matchNo}/scorelines?limit=${limit}`),
  valueScorelines: (limit = 20, sortBy = 'edge', signal?: string) => {
    const params = new URLSearchParams({
      limit: String(limit),
      sort_by: sortBy,
    })
    if (signal) {
      params.set('signal', signal)
    }
    return request<ScorelineRow[]>(`/api/scorelines/value?${params.toString()}`)
  },
  groupAdvance: () => request<GroupAdvanceRow[]>('/api/groups/advance'),
  matchReviews: (limit = 50, reviewBucket?: string) => {
    const params = new URLSearchParams({ limit: String(limit) })
    if (reviewBucket) params.set('review_bucket', reviewBucket)
    return request<MatchReviewRow[]>(`/api/reviews/matches?${params.toString()}`)
  },
  settleSimulator: (payload: {
    budget: number
    stake_per_combination: number
    bet_type: string
    selections: SimulatorSelection[]
  }) =>
    request<SimulatorResponse>('/api/simulator/settle', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
}
