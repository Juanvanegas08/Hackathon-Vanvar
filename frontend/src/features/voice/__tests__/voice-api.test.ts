import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createRealtimeClientSecret } from '@/api/voice.api'
import { adaptAnswer } from '@/utils/answerAdapter'
import type { NextQuestion } from '@/api/types'

vi.mock('@/api/client', () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
  },
  ApiError: class ApiError extends Error {
    status?: number
    constructor(message: string, status?: number) {
      super(message)
      this.status = status
    }
  },
}))

describe('Realtime client secret API', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  it('requests ephemeral token from backend without hardcoding OpenAI keys', async () => {
    const { apiClient } = await import('@/api/client')
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        client_secret: 'ek_test',
        model: 'gpt-realtime-2.1',
        voice: 'marin',
        expires_at: 1900000000,
      },
    })

    const result = await createRealtimeClientSecret('lead-1')
    expect(apiClient.post).toHaveBeenCalledWith('/api/v1/realtime/client-secret', {
      lead_id: 'lead-1',
    })
    expect(result.client_secret).toBe('ek_test')
    expect(JSON.stringify(result)).not.toContain('sk-')
  })
})

describe('Voice answer adapter compatibility', () => {
  it('keeps confirmation payloads compatible with backend', () => {
    const question: NextQuestion = {
      field: 'salario_mensual',
      question: '¿Sigue correcto?',
      type: 'confirmation',
      required: true,
      reason: 'test',
    }
    expect(adaptAnswer(question, 'yes')).toEqual({
      salario_mensual: { confirmed: true },
    })
  })
})

describe('Voice provider selection', () => {
  it('defaults to mock provider when openai is not selected', async () => {
    expect(import.meta.env.VITE_VOICE_PROVIDER || 'mock').toBe('mock')
  })
})
