import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/api/client'
import * as identityApi from '@/api/identity.api'
import * as leadsApi from '@/api/leads.api'
import * as recommendationsApi from '@/api/recommendations.api'
import { HomePage } from '@/pages/HomePage'
import { IdentityPage } from '@/pages/IdentityPage'
import { DemoPage } from '@/pages/DemoPage'
import { ResultsPage } from '@/pages/ResultsPage'
import { renderWithProviders } from '@/test/test-utils'
import { adaptAnswer, isConfirmationPayload } from '@/utils/answerAdapter'
import type { NextQuestion } from '@/api/types'

vi.mock('@/api/identity.api')
vi.mock('@/api/leads.api')
vi.mock('@/api/recommendations.api')

describe('Landing', () => {
  it('renders hero and primary CTA', () => {
    renderWithProviders(<HomePage />, { route: '/', path: '/' })
    expect(
      screen.getByRole('heading', {
        name: /tu camino a vivienda puede comenzar con una conversación/i,
      }),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /hablar ahora/i })).toBeInTheDocument()
    expect(screen.getByAltText('Colsubsidio')).toBeInTheDocument()
  })
})

describe('Identity lookup', () => {
  beforeEach(() => {
    vi.mocked(identityApi.listDemoIdentities).mockResolvedValue([
      {
        name: 'Laura Demo',
        document_number: '1000000001',
        document_type: 'CC',
        scenario: 'Afiliada categoría A',
      },
    ])
  })

  it('looks up a known affiliate', async () => {
    const user = userEvent.setup()
    vi.mocked(identityApi.lookupIdentity).mockResolvedValue({
      match_status: 'known_affiliate',
      known_lead: true,
      identity_verified: false,
      profile_source: 'mock_affiliation_service',
      prefilled_profile: { afiliado: true, categoria_afiliacion: 'A' },
      prefilled_fields: ['afiliado', 'categoria_afiliacion'],
      fields_to_confirm: ['salario_mensual'],
      consent_required: true,
      demo_mode: true,
    })

    renderWithProviders(<IdentityPage />, {
      route: '/identification',
      path: '/identification',
    })
    await user.type(screen.getByLabelText(/número de documento/i), '1000000001')
    await user.click(screen.getByRole('button', { name: /continuar/i }))

    await waitFor(() => {
      expect(identityApi.lookupIdentity).toHaveBeenCalledWith('CC', '1000000001')
    })
  })

  it('looks up a new lead document', async () => {
    const user = userEvent.setup()
    vi.mocked(identityApi.lookupIdentity).mockResolvedValue({
      match_status: 'new_lead',
      known_lead: false,
      identity_verified: false,
      profile_source: 'mock_affiliation_service',
      prefilled_profile: {},
      prefilled_fields: [],
      fields_to_confirm: [],
      consent_required: true,
      demo_mode: true,
    })

    renderWithProviders(<IdentityPage />, {
      route: '/identification',
      path: '/identification',
    })
    await user.type(screen.getByLabelText(/número de documento/i), '9999999999')
    await user.click(screen.getByRole('button', { name: /continuar/i }))

    await waitFor(() => {
      expect(identityApi.lookupIdentity).toHaveBeenCalledWith('CC', '9999999999')
    })
  })

  it('shows friendly backend disconnect message', async () => {
    const user = userEvent.setup()
    vi.mocked(identityApi.listDemoIdentities).mockResolvedValue([])
    vi.mocked(identityApi.lookupIdentity).mockRejectedValue(
      new ApiError(
        'No pudimos conectarnos con el servicio. Verifica que el backend esté disponible.',
      ),
    )

    renderWithProviders(<IdentityPage />, {
      route: '/identification',
      path: '/identification',
    })
    await user.type(screen.getByLabelText(/número de documento/i), '1000000001')
    await user.click(screen.getByRole('button', { name: /continuar/i }))

    expect(
      await screen.findByText(/no pudimos conectarnos con el servicio/i),
    ).toBeInTheDocument()
  })
})

describe('Answer adapter', () => {
  it('builds confirmation payloads', () => {
    const question: NextQuestion = {
      field: 'salario_mensual',
      question: '¿Sigue correcto?',
      type: 'confirmation',
      required: true,
      reason: 'test',
      confirmation_required: true,
      current_value: 1800000,
    }
    const confirmed = adaptAnswer(question, 'yes')
    expect(isConfirmationPayload(confirmed)).toBe(true)
    expect(confirmed).toEqual({ salario_mensual: { confirmed: true } })

    const updated = adaptAnswer(question, '2.000.000')
    expect(updated).toEqual({
      salario_mensual: { confirmed: false, new_value: 2000000 },
    })
  })

  it('maps currency answers for patch', () => {
    const question: NextQuestion = {
      field: 'ahorro',
      question: '¿Cuánto ahorro tienes?',
      type: 'currency',
      required: true,
      reason: 'test',
    }
    expect(adaptAnswer(question, '15.000.000')).toEqual({ ahorro: 15000000 })
  })
})

describe('Demo mode', () => {
  it('shows demo scenarios', async () => {
    vi.mocked(identityApi.listDemoIdentities).mockResolvedValue([
      {
        name: 'Laura Demo',
        document_number: '1000000001',
        document_type: 'CC',
        scenario: 'Afiliada conocida',
      },
      {
        name: 'No afiliado',
        document_number: '1000000005',
        document_type: 'CC',
        scenario: 'No afiliado conocido',
      },
      {
        name: 'Nuevo',
        document_number: '9999999999',
        document_type: 'CC',
        scenario: 'Lead nuevo',
      },
    ])

    renderWithProviders(<DemoPage />, { route: '/demo', path: '/demo' })
    expect(await screen.findByText(/modo demo para el jurado/i)).toBeInTheDocument()
    expect(await screen.findByText(/afiliada conocida/i)).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /iniciar escenario/i })).toHaveLength(3)
  })
})

describe('Results', () => {
  it('renders recommendations without duplicate canonical ids and keeps non-affiliates', async () => {
    vi.mocked(leadsApi.evaluateLead).mockResolvedValue({
      lead_id: 'lead-1',
      readiness_score: 72,
      confidence: 'medium',
      status: 'listo_para_asesor',
      complete_fields: ['afiliado'],
      missing_fields: [],
      positive_factors: ['Perfil completo'],
      gaps: ['Confirmar ahorro'],
      next_action: 'Hablar con asesor',
      warnings: [],
      disclaimer: 'Resultado orientativo. No constituye una aprobación de crédito hipotecario.',
    })
    vi.mocked(recommendationsApi.getRecommendations).mockResolvedValue({
      lead_id: 'lead-1',
      recommendation_status: 'completed',
      evaluated_projects: 29,
      recommended_projects: [
        {
          project_id: 'mongui',
          project_name: 'Monguí',
          canonical_project_id: 'mongui',
          rank: 1,
          compatibility_score: 81,
          confidence: 'medium',
          matched_factors: [
            { factor: 'afiliacion', message: 'Buena afinidad', contribution: 10 },
          ],
        },
        {
          project_id: 'zarzal',
          project_name: 'Zarzal',
          canonical_project_id: 'zarzal',
          rank: 2,
          compatibility_score: 70,
          confidence: 'low',
        },
      ],
      disclaimer: 'Orientativo',
      generated_at: '2026-07-22T00:00:00Z',
      profile_completeness: 80,
      overall_confidence: 'medium',
    })
    vi.mocked(leadsApi.getSummary).mockResolvedValue({
      lead_id: 'lead-1',
      headline: 'Perfil listo',
      basic_data: {},
      affiliation: { afiliado: false },
      financial_profile: {},
      household: {},
      readiness: {},
      gaps: [],
      fields_to_confirm: [],
      recommended_projects: [],
      confirmed_fields: [],
      field_sources: {},
      next_action: 'Continuar',
      disclaimer: 'Resultado orientativo. No constituye una aprobación de crédito hipotecario.',
    })

    renderWithProviders(<ResultsPage />, {
      route: '/results/lead-1',
      path: '/results/:leadId',
    })

    expect(
      await screen.findByText(/encontramos opciones que pueden ajustarse a ti/i),
    ).toBeInTheDocument()
    expect(screen.getByText('Monguí')).toBeInTheDocument()
    expect(screen.getAllByText('Monguí')).toHaveLength(1)
    expect(
      screen.getByText(/también encontramos opciones compatibles para ti/i),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/no constituye una aprobación de crédito hipotecario/i),
    ).toBeInTheDocument()
  })
})

describe('Consent API contract', () => {
  it('creates lead from identity with consent flag', async () => {
    vi.mocked(identityApi.createLeadFromIdentity).mockResolvedValue({
      lead: {
        id: 'lead-123',
        canal_origen: 'web',
        afiliacion_confirmada: true,
        known_lead: true,
      },
      identity_context: { known_lead: true, demo_mode: true },
      demo_mode: true,
    })

    await identityApi.createLeadFromIdentity('CC', '1000000001', true)
    expect(identityApi.createLeadFromIdentity).toHaveBeenCalledWith(
      'CC',
      '1000000001',
      true,
    )

    await identityApi.createLeadFromIdentity('CC', '1000000001', false)
    expect(identityApi.createLeadFromIdentity).toHaveBeenLastCalledWith(
      'CC',
      '1000000001',
      false,
    )
  })
})
