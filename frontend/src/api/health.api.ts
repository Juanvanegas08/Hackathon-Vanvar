import { apiClient } from '@/api/client'

export interface HealthResponse { status?: string; [key: string]: unknown }
export const checkHealth = async () => (await apiClient.get<HealthResponse>('/health')).data
