import { ApiError } from '@/api/client'

export const getErrorMessage = (error: unknown) =>
  error instanceof ApiError ? error.message : 'Ocurrió un error inesperado. Inténtalo de nuevo.'
