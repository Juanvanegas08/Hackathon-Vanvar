import type { LucideIcon } from 'lucide-react'
import type { AdvisorSummaryResponse, LeadResponse, ProjectRecommendation } from '@/api/types'
import { formatCOP } from '@/utils/currency'
import { resolveEngagementDisplay } from '@/utils/engagementDisplay'

export type AffinityBand = 'listo' | 'por_evaluar' | 'baja_afinidad'

export interface HistoricalBuyerProfile {
  total_buyers?: number
  affiliated_percentage?: number | null
  non_affiliated_percentage?: number | null
  category_distribution?: Record<string, number>
  salary_range_distribution?: Record<string, number>
  segments?: Record<string, number>
  dependents_distribution?: Record<string, number>
  dependents_average?: number | null
  household_composition_distribution?: Record<string, number>
  age_range_distribution?: Record<string, number>
  frequent_locations?: string[]
  [key: string]: unknown
}

export interface BuyerPersona {
  title: string
  segment: string
  urgency: 'Alta' | 'Media' | 'Baja'
  motivation: string
  profileBullets: string[]
  talkTracks: string[]
  objections: string[]
  closingAngle: string
  pptxSlide?: number | null
  pptxHref?: string | null
  projectName?: string | null
  historicalAvailable?: boolean
}

export interface CallInsight {
  label: string
  value: string
  tone: 'positive' | 'neutral' | 'warning'
  Icon?: LucideIcon
}

export interface ClosingStep {
  order: number
  title: string
  detail: string
}

const BUYER_PERSON_PPTX_HREF = '/docs/Buyer-Person.pptx'

/** Slide numbers from docs/Buyer Person.pptx (project buyer profiles). */
const BUYER_PERSON_SLIDES: Array<{ slide: number; names: string[] }> = [
  { slide: 1, names: ['bosques de arrayan', 'bosque de arrayan', 'arrayan'] },
  { slide: 2, names: ['bosques de turpial', 'bosque de turpial', 'turpial'] },
  { slide: 3, names: ['la macarena', 'macarena'] },
  { slide: 4, names: ['mongui', 'monguí'] },
  { slide: 5, names: ['pamplona'] },
  { slide: 6, names: ['reserva de guayacan', 'reserva de guayacán', 'guayacan', 'guayacán'] },
  { slide: 7, names: ['reserva de saman', 'reserva de samán', 'saman', 'samán'] },
  { slide: 8, names: ['inari'] },
  { slide: 9, names: ['la arboleda', 'arboleda'] },
  { slide: 10, names: ['los nogales', 'nogales'] },
  { slide: 11, names: ['karakali'] },
  { slide: 12, names: ['versalles'] },
  { slide: 13, names: ['abeto'] },
  { slide: 14, names: ['payande', 'payandé'] },
  { slide: 15, names: ['araucaria'] },
  { slide: 16, names: ['vibonce'] },
  { slide: 17, names: ['verde esperanza'] },
  { slide: 19, names: ['maipore', 'maiporé'] },
]

const timelineLabel: Record<string, string> = {
  inmediato: 'Quiere comprar de inmediato',
  '3_meses': 'Horizonte de unos 3 meses',
  '6_meses': 'Horizonte de unos 6 meses',
  '12_meses': 'Horizonte de unos 12 meses',
  mas_de_un_ano: 'Horizonte mayor a un año',
  no_definido: 'Plazo aún no definido',
}

const creditLabel: Record<string, string> = {
  sin_reportes: 'Sin reportes declarados',
  al_dia: 'Al día con créditos',
  atrasos_menores: 'Atrasos menores declarados',
  atrasos_mayores: 'Atrasos mayores declarados',
  en_proceso_normalizacion: 'En normalización',
  desconocida: 'Situación crediticia no clara',
}

const normalizeProjectKey = (value: string): string =>
  value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()

export const resolveBuyerPersonSlide = (projectName?: string | null): number | null => {
  if (!projectName) return null
  const key = normalizeProjectKey(projectName)
  for (const entry of BUYER_PERSON_SLIDES) {
    for (const name of entry.names) {
      const needle = normalizeProjectKey(name)
      if (key === needle || key.includes(needle) || needle.includes(key)) {
        return entry.slide
      }
    }
  }
  return null
}

export const getAffinityBand = (
  score?: number | null,
  band?: string | null,
): AffinityBand | null => {
  if (band === 'listo' || band === 'por_evaluar' || band === 'baja_afinidad') {
    return band
  }
  if (score == null || Number.isNaN(Number(score))) return null
  const value = Number(score)
  if (value >= 70) return 'listo'
  if (value >= 30) return 'por_evaluar'
  return 'baja_afinidad'
}

export const resolveLeadAffinity = (
  lead: LeadResponse,
  topProject?: ProjectRecommendation | null,
): { percent: number | null; band: AffinityBand | null } => {
  const percent =
    lead.affinity_percent != null
      ? Number(lead.affinity_percent)
      : topProject?.compatibility_score != null
        ? Number(topProject.compatibility_score)
        : null
  const band = getAffinityBand(percent, lead.affinity_band as string | null | undefined)
  return { percent, band }
}

export const affinityBandLabel = (band?: AffinityBand | null): string => {
  if (band === 'listo') return 'Listo'
  if (band === 'por_evaluar') return 'Por evaluar'
  if (band === 'baja_afinidad') return 'Baja afinidad'
  return 'Sin evaluar'
}

export const affinityBandClass = (band?: AffinityBand | null): string => {
  if (band === 'listo') return 'bg-[var(--color-green)] text-white'
  if (band === 'por_evaluar') return 'bg-[#c45c2a] text-white'
  if (band === 'baja_afinidad') return 'bg-[var(--color-muted)] text-white'
  return 'bg-[#f1f0eb] text-[var(--color-muted)]'
}

export const affiliationLabel = (lead: LeadResponse): string => {
  if (lead.afiliado === true) return 'Afiliado'
  if (lead.afiliado === false) return 'No afiliado'
  return 'Afiliación por confirmar'
}

export const briefingEyebrow = (band?: AffinityBand | null): string => {
  if (band === 'listo') return 'Briefing listo para cerrar'
  if (band === 'por_evaluar') return 'Briefing por evaluar'
  if (band === 'baja_afinidad') return 'Briefing baja afinidad'
  return 'Briefing del lead'
}

export const isEvaluatedLead = (lead: LeadResponse): boolean =>
  lead.affinity_percent != null ||
  Boolean(lead.affinity_band) ||
  Boolean(lead.top_project_name)

export const fieldLabel = (field: string): string => {
  const labels: Record<string, string> = {
    nombre: 'Nombre',
    telefono: 'Teléfono',
    correo: 'Correo',
    afiliado: 'Afiliación',
    categoria_afiliacion: 'Categoría',
    empresa: 'Empresa',
    salario_mensual: 'Salario laboral',
    ingreso_hogar: 'Ingreso del hogar',
    ahorro: 'Ahorro',
    obligaciones_mensuales: 'Obligaciones mensuales',
    personas_hogar: 'Personas en el hogar',
    personas_a_cargo: 'Personas a cargo',
    tiene_vivienda: 'Vivienda propia',
    situacion_crediticia: 'Situación crediticia',
    ubicacion_deseada: 'Zona deseada',
    plazo_compra: 'Plazo de compra',
    proyecto_interes: 'Proyecto de interés',
    consentimiento: 'Consentimiento',
    data_consent: 'Consentimiento de datos',
  }
  return labels[field] ?? field.replaceAll('_', ' ')
}

const topDistributionLabel = (
  distribution?: Record<string, number> | null,
): string | null => {
  if (!distribution) return null
  const entries = Object.entries(distribution).sort((a, b) => b[1] - a[1])
  if (!entries.length) return null
  const [label, pct] = entries[0]
  return `${label} (${Math.round(pct)}%)`
}

const readHistoricalProfile = (
  topProject?: ProjectRecommendation | null,
): HistoricalBuyerProfile | null => {
  if (!topProject) return null
  const direct = topProject.historical_profile
  if (direct && typeof direct === 'object') return direct as HistoricalBuyerProfile
  const nested = topProject.metadata?.historical_profile
  if (nested && typeof nested === 'object') return nested as HistoricalBuyerProfile
  return null
}

const buildFallbackBuyerPersona = (
  lead: LeadResponse,
  summary: AdvisorSummaryResponse,
  topProject?: ProjectRecommendation | null,
): BuyerPersona => {
  const affiliated = lead.afiliado === true
  const category = lead.categoria_afiliacion
  const savings = lead.ahorro ?? 0
  const householdIncome = lead.ingreso_hogar ?? lead.salario_mensual ?? 0
  const timeline = lead.plazo_compra ?? 'no_definido'
  const hasDependents = (lead.personas_a_cargo ?? 0) > 0
  const { percent } = resolveLeadAffinity(lead, topProject)
  const affinityScore = percent ?? Number(summary.readiness?.score ?? 0)

  let title = 'Comprador explorador'
  let segment = 'Perfil en construcción'
  let motivation = 'Está buscando orientación para acercarse a vivienda.'

  if (affiliated && category === 'A' && hasDependents) {
    title = 'Familia afiliada con prioridad de vivienda'
    segment = 'Afiliado categoría A · hogar con personas a cargo'
    motivation =
      'Necesita una opción asequible y clara, con acompañamiento cercano para avanzar rápido.'
  } else if (affiliated && category === 'A') {
    title = 'Afiliado categoría A con foco en primer hogar'
    segment = 'Afiliado categoría A'
    motivation = 'Busca una solución de vivienda alineada a su capacidad y beneficios de afiliado.'
  } else if (affiliated && category === 'B') {
    title = 'Afiliado de capacidad media'
    segment = 'Afiliado categoría B'
    motivation = 'Puede explorar proyectos de rango medio con una conversación comercial concreta.'
  } else if (affiliated && category === 'C') {
    title = 'Afiliado de mayor capacidad'
    segment = 'Afiliado categoría C'
    motivation = 'Valora proyectos con mejor ubicación, acabados o etapas más avanzadas.'
  } else if (lead.afiliado === false) {
    title = 'Comprador no afiliado con interés real'
    segment = 'No afiliado · cupo comercial 10%'
    motivation =
      'No debe descartarse: conviene presentar opciones compatibles y explicar disponibilidad comercial.'
  }

  if (timeline === 'inmediato' || timeline === '3_meses') {
    motivation += ' Tiene urgencia de avance en el corto plazo.'
  }

  const urgency: BuyerPersona['urgency'] =
    timeline === 'inmediato' || timeline === '3_meses'
      ? 'Alta'
      : timeline === '6_meses' || affinityScore >= 70
        ? 'Media'
        : 'Baja'

  const profileBullets = [
    affiliated
      ? `Afiliado${category ? ` categoría ${category}` : ''}${lead.empresa ? ` · ${lead.empresa}` : ''}`
      : lead.afiliado === false
        ? 'No afiliado — continuar con contexto 90/10'
        : 'Afiliación aún por confirmar',
    householdIncome
      ? `Ingreso de referencia: ${formatCOP(householdIncome)}`
      : 'Ingreso aún no consolidado',
    savings > 0 ? `Ahorro identificado: ${formatCOP(savings)}` : 'Ahorro por validar en llamada',
    lead.ubicacion_deseada
      ? `Zona deseada: ${lead.ubicacion_deseada}`
      : 'Zona deseada pendiente',
    timelineLabel[timeline] ?? 'Plazo por definir',
    hasDependents
      ? `Grupo familiar con ${lead.personas_a_cargo} persona(s) a cargo`
      : 'Sin personas a cargo registradas',
  ]

  const talkTracks = affiliated
    ? [
        'Abre reconociendo su afiliación y que ya hay un perfil avanzado.',
        'Valida solo los datos que aún requieren confirmación.',
        'Presenta máximo 2 proyectos y pide una preferencia clara.',
      ]
    : [
        'No uses lenguaje de rechazo; enfócate en opciones compatibles.',
        'Explica con naturalidad la disponibilidad para no afiliados.',
        'Cierra con una próxima acción concreta (visita o seguimiento).',
      ]

  const objections =
    lead.afiliado === false
      ? [
          '“¿Me van a dejar por fuera por no estar afiliado?” → Explica cupo y alternativas.',
          '“No tengo claro el presupuesto” → Usa rangos y proyectos ancla.',
        ]
      : savings < 10_000_000
        ? [
            '“Me falta ahorro” → Propón ruta de nutrición + proyecto compatible.',
            '“¿Puedo alcanzar este proyecto?” → Enfatiza orientación, no aprobación.',
          ]
        : [
            '“Quiero pensarlo” → Resume fit y agenda seguimiento en 48h.',
            '“¿Cuál es el mejor?” → Compara 2 opciones con pros concretos.',
          ]

  const closingAngle =
    affinityScore >= 70
      ? 'Perfil listo para cierre comercial: agenda visita o formaliza interés en el proyecto top.'
      : 'Todavía conviene nutrir el perfil, pero puedes dejar una opción ancla y un próximo paso.'

  const projectName = topProject?.project_name ?? lead.top_project_name ?? null
  const pptxSlide = resolveBuyerPersonSlide(projectName)

  return {
    title,
    segment,
    urgency,
    motivation,
    profileBullets,
    talkTracks,
    objections,
    closingAngle,
    pptxSlide,
    pptxHref: pptxSlide ? BUYER_PERSON_PPTX_HREF : null,
    projectName,
    historicalAvailable: false,
  }
}

export const buildBuyerPersona = (
  lead: LeadResponse,
  summary: AdvisorSummaryResponse,
  topProject?: ProjectRecommendation | null,
): BuyerPersona => {
  const projectName = topProject?.project_name ?? lead.top_project_name ?? null
  const historical = readHistoricalProfile(topProject)
  const pptxSlide = resolveBuyerPersonSlide(projectName)

  if (!historical || !(historical.total_buyers && historical.total_buyers > 0)) {
    const fallback = buildFallbackBuyerPersona(lead, summary, topProject)
    if (projectName) {
      return {
        ...fallback,
        title: `Buyer persona · ${projectName}`,
        segment: fallback.historicalAvailable
          ? fallback.segment
          : 'Sin buyer persona histórico para este proyecto',
        pptxSlide,
        pptxHref: pptxSlide ? BUYER_PERSON_PPTX_HREF : null,
        projectName,
      }
    }
    return fallback
  }

  const timeline = lead.plazo_compra ?? 'no_definido'
  const salary = topDistributionLabel(historical.salary_range_distribution)
  const segmentPop = topDistributionLabel(historical.segments)
  const household = topDistributionLabel(historical.household_composition_distribution)
  const age = topDistributionLabel(historical.age_range_distribution)
  const affiliatedPct = historical.affiliated_percentage
  const nonAffiliatedPct = historical.non_affiliated_percentage

  const urgency: BuyerPersona['urgency'] =
    timeline === 'inmediato' || timeline === '3_meses'
      ? 'Alta'
      : timeline === '6_meses'
        ? 'Media'
        : 'Baja'

  const affiliationText =
    affiliatedPct != null
      ? `${Math.round(affiliatedPct)}% afiliados` +
        (nonAffiliatedPct != null ? ` · ${Math.round(nonAffiliatedPct)}% no afiliados` : '')
      : 'Mix de afiliación histórico no disponible'

  const motivationParts = [
    `El comprador típico de ${projectName ?? 'este proyecto'} se alinea con ${affiliationText.toLowerCase()}.`,
    salary ? `Predomina el rango salarial ${salary}.` : null,
    segmentPop ? `Segmento dominante: ${segmentPop}.` : null,
    timeline === 'inmediato' || timeline === '3_meses'
      ? 'El lead actual tiene urgencia de avance en el corto plazo.'
      : null,
  ].filter(Boolean)

  const profileBullets = [
    `Muestra histórica: ${historical.total_buyers} compradores`,
    affiliationText,
    salary ? `Rango salarial dominante: ${salary}` : 'Rango salarial sin dato histórico',
    segmentPop ? `Segmento poblacional: ${segmentPop}` : 'Segmento poblacional sin dato',
    age ? `Rango de edad dominante: ${age}` : 'Edad histórica sin dato',
    household
      ? `Composición de hogar dominante: ${household}`
      : historical.dependents_average != null
        ? `Promedio de beneficiarios/PAC: ${historical.dependents_average}`
        : 'Composición de hogar sin dato',
    lead.afiliado === true
      ? `Lead actual: afiliado${lead.categoria_afiliacion ? ` cat. ${lead.categoria_afiliacion}` : ''}`
      : lead.afiliado === false
        ? 'Lead actual: no afiliado'
        : 'Lead actual: afiliación por confirmar',
  ]

  const { percent } = resolveLeadAffinity(lead, topProject)
  const closingAngle =
    (percent ?? 0) >= 70
      ? `Alta afinidad con ${projectName}: agenda visita o formaliza interés.`
      : (percent ?? 0) >= 30
        ? `Afinidad intermedia con ${projectName}: valida encaje comercial antes de cerrar.`
        : `Baja afinidad con ${projectName}: usa el buyer person como referencia y nutre el perfil.`

  return {
    title: `Buyer persona · ${projectName}`,
    segment: [
      affiliationText,
      salary ? `Salario ${salary}` : null,
      segmentPop,
    ]
      .filter(Boolean)
      .join(' · '),
    urgency,
    motivation: motivationParts.join(' '),
    profileBullets,
    talkTracks: [
      `Enmarca la conversación con el perfil histórico de ${projectName}.`,
      'Compara al lead con los ejes del buyer person (afiliación, salario, hogar).',
      'Presenta el proyecto top y una alternativa cercana al mismo perfil.',
    ],
    objections:
      lead.afiliado === false
        ? [
            '“¿Me van a dejar por fuera por no estar afiliado?” → Explica cupo y el mix histórico del proyecto.',
            '“No tengo claro el presupuesto” → Usa el rango salarial dominante del buyer person.',
          ]
        : [
            '“¿Encajo con este proyecto?” → Contrasta su perfil con el buyer person histórico.',
            '“Quiero pensarlo” → Resume fit y agenda seguimiento en 48h.',
          ],
    closingAngle,
    pptxSlide,
    pptxHref: pptxSlide ? BUYER_PERSON_PPTX_HREF : null,
    projectName,
    historicalAvailable: true,
  }
}

export const buildCallInsights = (
  lead: LeadResponse,
  summary: AdvisorSummaryResponse,
  topProject?: ProjectRecommendation | null,
): CallInsight[] => {
  const insights: CallInsight[] = []

  if (lead.known_lead) {
    insights.push({
      label: 'Identidad',
      value: lead.afiliado
        ? 'Afiliado conocido con información precargada'
        : 'Persona conocida; afiliación no activa o no afiliada',
      tone: 'positive',
    })
  } else {
    insights.push({
      label: 'Identidad',
      value: 'Lead nuevo construido en la conversación',
      tone: 'neutral',
    })
  }

  if (lead.identity_verified === false) {
    insights.push({
      label: 'Verificación',
      value: 'Identidad no verificada (sin OTP). Confirmar datos sensibles al hablar.',
      tone: 'warning',
    })
  }

  const confirmed = summary.confirmed_fields?.length ?? 0
  insights.push({
    label: 'Datos consolidados',
    value: `${confirmed} campo(s) confirmados · ${summary.fields_to_confirm.length} por confirmar`,
    tone: summary.fields_to_confirm.length ? 'warning' : 'positive',
  })

  if (lead.situacion_crediticia) {
    insights.push({
      label: 'Crédito declarado',
      value: creditLabel[lead.situacion_crediticia] ?? lead.situacion_crediticia,
      tone:
        lead.situacion_crediticia === 'atrasos_mayores' ? 'warning' : 'neutral',
    })
  }

  if (lead.proyecto_interes) {
    insights.push({
      label: 'Interés declarado',
      value: `Mencionó interés en ${lead.proyecto_interes}`,
      tone: 'positive',
    })
  }

  if (lead.ubicacion_deseada) {
    insights.push({
      label: 'Preferencia de zona',
      value: lead.ubicacion_deseada,
      tone: 'positive',
    })
  }

  if (lead.engagement_label) {
    const display = resolveEngagementDisplay(lead.engagement_label)
    const score =
      typeof lead.engagement_score === 'number' ? ` · ${lead.engagement_score}/100` : ''
    const reason = lead.engagement_reason ? ` — ${lead.engagement_reason}` : ''
    insights.push({
      label: 'Sentimiento (Laura)',
      value: `${display.headline}${score}${reason}`,
      tone: display.tone,
      Icon: display.Icon,
    })
  }

  const { percent, band } = resolveLeadAffinity(lead, topProject)
  insights.push({
    label: 'Afinidad vivienda',
    value:
      percent != null
        ? `${Math.round(percent)}% · ${affinityBandLabel(band)}${topProject ? ` · ${topProject.project_name}` : ''}`
        : 'Sin afinidad calculada aún',
    tone: band === 'listo' ? 'positive' : band === 'por_evaluar' ? 'neutral' : 'warning',
  })

  return insights
}

export const buildClosingPlaybook = (
  lead: LeadResponse,
  summary: AdvisorSummaryResponse,
  topProject?: ProjectRecommendation | null,
): ClosingStep[] => {
  const pending = summary.fields_to_confirm.map(fieldLabel)
  const steps: ClosingStep[] = [
    {
      order: 1,
      title: 'Romper el hielo con contexto',
      detail: lead.known_lead
        ? 'Menciona que ya tienen parte del perfil y que la llamada será para confirmar y avanzar.'
        : 'Agradece el tiempo y resume en una frase lo que entendieron de su búsqueda.',
    },
    {
      order: 2,
      title: 'Validar pendientes críticos',
      detail: pending.length
        ? `Confirma solo: ${pending.slice(0, 3).join(', ')}.`
        : 'No hay pendientes críticos; pasa directo a opciones.',
    },
    {
      order: 3,
      title: 'Presentar la mejor opción',
      detail: topProject
        ? `Ancla la conversación en ${topProject.project_name} (${Math.round(topProject.compatibility_score)}% afinidad) y una alternativa.`
        : 'Si aún no hay top project, pide zona y presupuesto para acotar.',
    },
    {
      order: 4,
      title: 'Cerrar con próxima acción',
      detail: summary.next_action,
    },
  ]
  return steps
}

export const formatStatus = (status?: string | null): string => {
  if (!status) return 'Sin estado'
  if (status === 'listo' || status === 'listo_para_asesor') return 'Listo'
  if (status === 'por_evaluar' || status === 'en_evaluacion') return 'Por evaluar'
  if (status === 'baja_afinidad' || status === 'nutricion' || status === 'ruta_nutricion') {
    return 'Baja afinidad'
  }
  return status.replaceAll('_', ' ')
}
