import { apiClient } from '@/api/client'

export type PhoneCallMode = 'now' | 'schedule'
export type DocumentType = 'CC' | 'CE' | 'PP' | 'NIT'

export interface PhoneLookupRequest {
  document_type: DocumentType
  document_number: string
}

export interface PhoneLookupResponse {
  known_lead: boolean
  has_phone: boolean
  nombre?: string | null
  phone_last4?: string | null
  message: string
}

export interface PhoneCallRequest {
  document_type: DocumentType
  document_number: string
  data_consent: boolean
  mode: PhoneCallMode
  scheduled_at?: string | null
  confirm_stored_phone?: boolean
  phone?: string
  country_code?: string
  nombre?: string
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

export const lookupPhoneIdentity = async (
  payload: PhoneLookupRequest,
): Promise<PhoneLookupResponse> => {
  const { data } = await apiClient.post<PhoneLookupResponse>(
    '/api/v1/phone/lookup',
    payload,
  )
  return data
}

export const requestPhoneCall = async (
  payload: PhoneCallRequest,
): Promise<PhoneCallResponse> => {
  const { data } = await apiClient.post<PhoneCallResponse>('/api/v1/phone/calls', payload, {
    timeout: 60_000,
  })
  return data
}
