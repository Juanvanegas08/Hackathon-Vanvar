import { apiClient } from '@/api/client'
import type { RecommendationResponse } from '@/api/types'

export const getRecommendations = async (leadId: string, options?: { limit?: number; includeUnavailable?: boolean; minScore?: number }) =>
  (await apiClient.get<RecommendationResponse>(`/api/v1/leads/${leadId}/recommendations`, {
    params: { limit: options?.limit, include_unavailable: options?.includeUnavailable, min_score: options?.minScore },
  })).data
