import { describe, expect, it } from 'vitest'
import type { AdvisorSummaryResponse, LeadResponse } from '@/api/types'
import {
  affinityBandLabel,
  buildBuyerPersona,
  buildCallInsights,
  buildClosingPlaybook,
  fieldLabel,
  getAffinityBand,
  resolveBuyerPersonSlide,
  resolveLeadAffinity,
} from '@/utils/advisorBriefing'

const leadBase: LeadResponse = {
  id: 'lead-1',
  canal_origen: 'voz',
  afiliacion_confirmada: false,
  nombre: 'Laura Demo',
  document_type: 'CC',
  document_number: '1000000001',
  afiliado: true,
  categoria_afiliacion: 'A',
  empresa: 'Empresa Demo',
  salario_mensual: 2_500_000,
  ingreso_hogar: 4_000_000,
  ahorro: 15_000_000,
  personas_a_cargo: 1,
  plazo_compra: '3_meses',
  ubicacion_deseada: 'Soacha',
  known_lead: true,
  identity_verified: false,
  situacion_crediticia: 'al_dia',
  proyecto_interes: 'Monguí',
}

const summaryBase: AdvisorSummaryResponse = {
  lead_id: 'lead-1',
  headline: 'Lead afiliado conocido con datos precargados',
  basic_data: { nombre: 'Laura Demo', telefono: null, correo: null, canal_origen: 'voz' },
  affiliation: { is_affiliated: true, category: 'A', confirmed: false },
  financial_profile: {
    personal_income: 2_500_000,
    household_income: 4_000_000,
    savings: 15_000_000,
    monthly_obligations: null,
  },
  household: { personas_hogar: 3, personas_a_cargo: 1, tiene_vivienda: false },
  readiness: { score: 78, status: 'listo_para_asesor', confidence: 'medium' },
  gaps: [],
  fields_to_confirm: ['salario_mensual'],
  recommended_projects: [],
  confirmed_fields: ['afiliado', 'categoria_afiliacion'],
  field_sources: {},
  next_action: 'Agendar conversación comercial',
  disclaimer: 'Resultado orientativo.',
}

describe('advisorBriefing', () => {
  it('maps field labels in Spanish', () => {
    expect(fieldLabel('salario_mensual')).toBe('Salario laboral')
  })

  it('classifies affinity bands by housing compatibility', () => {
    expect(getAffinityBand(82)).toBe('listo')
    expect(getAffinityBand(55)).toBe('por_evaluar')
    expect(getAffinityBand(25)).toBe('baja_afinidad')
    expect(affinityBandLabel('por_evaluar')).toBe('Por evaluar')
  })

  it('resolves buyer person pptx slides by project name', () => {
    expect(resolveBuyerPersonSlide('Monguí')).toBe(4)
    expect(resolveBuyerPersonSlide('La Macarena')).toBe(3)
  })

  it('builds an affiliate buyer persona with high urgency', () => {
    const persona = buildBuyerPersona(leadBase, summaryBase)
    expect(persona.title).toMatch(/Familia afiliada|Afiliado categoría A/i)
    expect(persona.urgency).toBe('Alta')
    expect(persona.talkTracks.length).toBeGreaterThan(0)
  })

  it('builds historical buyer persona from top project profile', () => {
    const persona = buildBuyerPersona(leadBase, summaryBase, {
      project_id: 'mongui',
      project_name: 'Monguí',
      canonical_project_id: 'mongui',
      rank: 1,
      compatibility_score: 91,
      confidence: 'high',
      historical_profile_available: true,
      historical_profile: {
        total_buyers: 100,
        affiliated_percentage: 66,
        non_affiliated_percentage: 34,
        salary_range_distribution: { 'Hasta 2 smlv': 87 },
        segments: { Medio: 39 },
        age_range_distribution: { '20 a 35 años': 56 },
      },
    })
    expect(persona.title).toBe('Buyer persona · Monguí')
    expect(persona.historicalAvailable).toBe(true)
    expect(persona.pptxSlide).toBe(4)
    expect(persona.pptxHref).toBe('/docs/Buyer-Person.pptx')
    expect(persona.profileBullets.some((item) => item.includes('66%'))).toBe(true)
  })

  it('surfaces call insights and closing steps', () => {
    const insights = buildCallInsights(
      {
        ...leadBase,
        engagement_label: 'interesado',
        engagement_score: 90,
        engagement_reason: 'Muy colaborador',
      },
      summaryBase,
      {
        project_id: 'p1',
        project_name: 'Monguí',
        canonical_project_id: 'mongui',
        rank: 1,
        compatibility_score: 88,
        confidence: 'high',
      },
    )
    expect(insights.some((item) => item.label === 'Identidad')).toBe(true)
    expect(insights.some((item) => item.label === 'Interés declarado')).toBe(true)
    expect(insights.some((item) => item.label === 'Predisposición (Laura)')).toBe(true)
    expect(insights.some((item) => item.label === 'Afinidad vivienda')).toBe(true)
    expect(resolveLeadAffinity(leadBase, {
      project_id: 'p1',
      project_name: 'Monguí',
      canonical_project_id: 'mongui',
      rank: 1,
      compatibility_score: 88,
      confidence: 'high',
    }).band).toBe('listo')

    const steps = buildClosingPlaybook(leadBase, summaryBase, {
      project_id: 'p1',
      project_name: 'Monguí',
      canonical_project_id: 'mongui',
      rank: 1,
      compatibility_score: 88,
      confidence: 'high',
    })
    expect(steps).toHaveLength(4)
    expect(steps[2]?.detail).toMatch(/Monguí/)
  })
})
