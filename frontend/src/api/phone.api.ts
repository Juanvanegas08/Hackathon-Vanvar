import { apiClient } from '@/api/client'

export type PhoneCallMode = 'now' | 'schedule'

export interface PhoneCallRequest {
  phone: string
  mode: PhoneCallMode
  scheduled_at?: string | null
  document_type: 'CC' | 'CE' | 'PP' | 'NIT'
  document_number: string
  data_consent: boolean
}

export interface PhoneCallResponse {
  mode: PhoneCallMode
  lead_id: string
  phone: string
  call_sid?: string | null
  scheduled_call_id?: string | null
  scheduled_at?: string | null
  status: string
  message: string
}

export const requestPhoneCall = async (
  payload: PhoneCallRequest,
): Promise<PhoneCallResponse> => {
  const { data } = await apiClient.post<PhoneCallResponse>('/api/v1/phone/calls', payload, {
    timeout: 60_000,
  })
  return data
}
