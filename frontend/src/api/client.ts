import axios, { AxiosError } from 'axios'

export class ApiError extends Error {
  readonly status?: number
  readonly detail?: unknown

  constructor(message: string, status?: number, detail?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

const friendlyMessage = (error: AxiosError<{ detail?: unknown }>): string => {
  if (error.code === 'ECONNABORTED') {
    return 'La solicitud tardó demasiado. El recomendador sigue procesando; inténtalo de nuevo en unos segundos.'
  }
  if (!error.response) {
    return 'No pudimos conectarnos con el servicio. Verifica que el backend esté disponible.'
  }
  if (error.response.status === 404) return 'No encontramos la información solicitada.'
  if (error.response.status === 422) {
    return formatValidationDetail(error.response.data?.detail)
  }
  if (error.response.status >= 500) {
    return 'El servicio presentó un problema. Inténtalo de nuevo en unos minutos.'
  }
  const detail = error.response.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  return 'No pudimos completar la solicitud. Inténtalo de nuevo.'
}

const formatValidationDetail = (detail: unknown): string => {
  if (typeof detail === 'string' && detail.trim()) return detail
  if (!Array.isArray(detail) || detail.length === 0) {
    return 'Revisa los datos ingresados e inténtalo de nuevo.'
  }
  const parts = detail.map((item) => {
    if (!item || typeof item !== 'object') return null
    const row = item as { loc?: unknown[]; msg?: string; type?: string }
    const field = Array.isArray(row.loc)
      ? row.loc.filter((p) => p !== 'body').join('.')
      : ''
    const msg = row.msg || 'dato inválido'
    if (field === 'scheduled_at') {
      return 'La fecha/hora programada no es válida.'
    }
    if (field === 'phone') return `Teléfono: ${msg}`
    if (field === 'country_code') return `Indicativo: ${msg}`
    if (field === 'nombre') return `Nombre: ${msg}`
    if (field === 'document_number') return `Documento: ${msg}`
    if (field === 'document_type') return 'Tipo de documento inválido.'
    if (field === 'data_consent') return 'Debes aceptar el consentimiento de datos.'
    if (field === 'mode') return 'Elige llamar ahora o programar.'
    return field ? `${field}: ${msg}` : msg
  })
  return parts.filter(Boolean).join(' ') || 'Revisa los datos ingresados e inténtalo de nuevo.'
}

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8100',
  timeout: 15_000,
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: unknown }>) =>
    Promise.reject(
      new ApiError(
        friendlyMessage(error),
        error.response?.status,
        error.response?.data?.detail,
      ),
    ),
)
