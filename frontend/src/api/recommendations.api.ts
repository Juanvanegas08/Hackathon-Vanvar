import { apiClient } from '@/api/client'
import type { RecommendationResponse } from '@/api/types'

/** El recomendador OpenAI suele superar el timeout global de 15s. */
const RECOMMENDATION_TIMEOUT_MS = 90_000

export const getRecommendations = async (
  leadId: string,
  options?: {
    limit?: number
    includeUnavailable?: boolean
    minScore?: number
    preferOpenai?: boolean
  },
) =>
  (
    await apiClient.get<RecommendationResponse>(`/api/v1/leads/${leadId}/recommendations`, {
      params: {
        limit: options?.limit,
        include_unavailable: options?.includeUnavailable,
        min_score: options?.minScore,
        prefer_openai: options?.preferOpenai,
      },
      // Determinístico es rápido; OpenAI puede superar el timeout global.
      timeout: options?.preferOpenai === false ? 20_000 : RECOMMENDATION_TIMEOUT_MS,
    })
  ).data
