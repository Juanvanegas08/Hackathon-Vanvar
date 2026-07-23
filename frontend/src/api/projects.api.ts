import { apiClient } from '@/api/client'

export interface Project { id: string; nombre: string; [key: string]: unknown }
export interface ProjectFilters { disponible?: boolean; municipio?: string; departamento?: string; nombre?: string }

export const listProjects = async (filters?: ProjectFilters) => (await apiClient.get<Project[]>('/api/v1/projects', { params: filters })).data
export const getProject = async (projectId: string) => (await apiClient.get<Project>(`/api/v1/projects/${projectId}`)).data
