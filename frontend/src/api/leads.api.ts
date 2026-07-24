import { apiClient } from '@/api/client'
import type { AdvisorSummaryResponse, LeadResponse, LeadUpdate, NextQuestionResponse, ReadinessResponse } from '@/api/types'

const prefix = '/api/v1/leads'
export const createLead = async (payload: LeadUpdate) => (await apiClient.post<LeadResponse>(prefix, payload)).data
export const getLead = async (leadId: string) => (await apiClient.get<LeadResponse>(`${prefix}/${leadId}`)).data
export const listLeads = async () => (await apiClient.get<LeadResponse[]>(prefix)).data
export const updateLead = async (leadId: string, payload: LeadUpdate) => (await apiClient.patch<LeadResponse>(`${prefix}/${leadId}`, payload)).data
export const getNextQuestion = async (leadId: string) => (await apiClient.get<NextQuestionResponse>(`${prefix}/${leadId}/next-question`)).data
export const evaluateLead = async (leadId: string) => (await apiClient.post<ReadinessResponse>(`${prefix}/${leadId}/evaluate`)).data
export const getSummary = async (leadId: string) =>
  (
    await apiClient.get<AdvisorSummaryResponse>(`${prefix}/${leadId}/summary`, {
      // Summary también invoca el recomendador OpenAI.
      timeout: 90_000,
    })
  ).data
