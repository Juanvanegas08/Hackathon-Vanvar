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
  if (error.response.status === 422) return 'Revisa los datos ingresados e inténtalo de nuevo.'
  if (error.response.status >= 500) {
    return 'El servicio presentó un problema. Inténtalo de nuevo en unos minutos.'
  }
  return 'No pudimos completar la solicitud. Inténtalo de nuevo.'
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
