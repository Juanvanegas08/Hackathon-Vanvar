import { apiClient } from '@/api/client'
import type { DemoIdentityItem, IdentityLookupResponse, LeadFromIdentityResponse, LeadResponse } from '@/api/types'

const prefix = '/api/v1'
export const lookupIdentity = async (documentType: string, documentNumber: string) => (await apiClient.post<IdentityLookupResponse>(`${prefix}/identity/lookup`, { document_type: documentType, document_number: documentNumber })).data
export const createLeadFromIdentity = async (documentType: string, documentNumber: string, dataConsent: boolean) => (await apiClient.post<LeadFromIdentityResponse>(`${prefix}/leads/from-identity`, { document_type: documentType, document_number: documentNumber, data_consent: dataConsent })).data
export const confirmPrefilledData = async (leadId: string, confirmations: Record<string, { confirmed: boolean; new_value?: unknown }>) => (await apiClient.post<LeadResponse>(`${prefix}/leads/${leadId}/confirm-prefilled-data`, { confirmations })).data
export const listDemoIdentities = async () => (await apiClient.get<DemoIdentityItem[]>(`${prefix}/demo/identities`)).data
