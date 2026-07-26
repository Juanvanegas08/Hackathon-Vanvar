import { apiClient } from '@/api/client'

export interface RealtimeClientSecretResponse {
  client_secret: string
  expires_at?: number | null
  model: string
  voice: string
  session_id?: string | null
}

export interface VoiceContextResponse {
  lead_id: string
  known_lead: boolean
  display_name?: string | null
  identity_status?: string | null
  profile_completed: boolean
  progress: number
  next_question?: {
    field: string
    question: string
    type: string
    required?: boolean
    reason?: string
    confirmation_required?: boolean
    current_value?: unknown
    source?: string | null
  } | null
  conversation_opening: string
  confirmed_fields: string[]
  fields_to_confirm: string[]
  warnings: string[]
  demo_mode: boolean
}

export interface VoiceAnswerPayload {
  field: string
  raw_transcript?: string | null
  normalized_value?: string | number | boolean | null
  action: 'answer' | 'confirm' | 'correct' | 'skip'
}

export interface VoiceAnswerResponse {
  accepted: boolean
  updated_field?: string | null
  profile_completed: boolean
  progress: number
  next_question?: VoiceContextResponse['next_question']
  assistant_guidance: string
  clarification_required?: boolean
  validation_message?: string | null
  warnings?: string[]
}

export interface VoiceCompleteResponse {
  completed: boolean
  readiness: {
    score: number
    status: string
    confidence: string
  }
  recommendations_count: number
  top_project?: {
    id: string
    name: string
    reason?: string
    brochure_url?: string
  } | null
  next_action: string
  navigation_path: string
  assistant_closing: string
  disclaimer: string
  spoken_summary?: string | null
  recommended_projects?: Array<{
    project_name: string
    reason?: string | null
    probability?: number | null
    compatibility_score?: number
    brochure_url?: string | null
    rank?: number
  }>
  profile_json_path?: string | null
  engine?: string | null
  engagement_label?: string | null
  engagement_score?: number | null
  engagement_reason?: string | null
}

export type EngagementLabel =
  | 'interesado'
  | 'indeciso'
  | 'molesto'
  | 'trolleando'
  | 'ocupado'
  | 'desconocido'

export const createRealtimeClientSecret = async (leadId: string) =>
  (
    await apiClient.post<RealtimeClientSecretResponse>('/api/v1/realtime/client-secret', {
      lead_id: leadId,
    })
  ).data

export const getVoiceContext = async (leadId: string) =>
  (await apiClient.get<VoiceContextResponse>(`/api/v1/voice/leads/${leadId}/context`)).data

export const submitVoiceAnswer = async (leadId: string, payload: VoiceAnswerPayload) =>
  (await apiClient.post<VoiceAnswerResponse>(`/api/v1/voice/leads/${leadId}/answer`, payload))
    .data

export const completeVoiceProfile = async (
  leadId: string,
  payload?: {
    engagement_label?: EngagementLabel | null
    engagement_score?: number | null
    engagement_reason?: string | null
  },
) =>
  (
    await apiClient.post<VoiceCompleteResponse>(
      `/api/v1/voice/leads/${leadId}/complete`,
      // El cierre llama al recomendador OpenAI; suele tardar >15s del timeout global.
      payload ?? {},
      { timeout: 90_000 },
    )
  ).data

export interface VoiceEngagementPayload {
  label: EngagementLabel
  score?: number | null
  reason?: string | null
}

export interface VoiceEngagementResponse {
  accepted: boolean
  engagement_label: EngagementLabel | string
  engagement_score?: number | null
  engagement_reason?: string | null
  engagement_updated_at?: string | null
}

export const reportVoiceEngagement = async (
  leadId: string,
  payload: VoiceEngagementPayload,
) =>
  (
    await apiClient.post<VoiceEngagementResponse>(
      `/api/v1/voice/leads/${leadId}/engagement`,
      payload,
    )
  ).data
