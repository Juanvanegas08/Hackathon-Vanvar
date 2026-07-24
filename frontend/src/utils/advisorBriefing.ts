import type { AdvisorSummaryResponse, LeadResponse, ProjectRecommendation } from '@/api/types'
import { formatCOP } from '@/utils/currency'

export interface BuyerPersona {
  title: string
  segment: string
  urgency: 'Alta' | 'Media' | 'Baja'
  motivation: string
  profileBullets: string[]
  talkTracks: string[]
  objections: string[]
  closingAngle: string
}

export interface CallInsight {
  label: string
  value: string
  tone: 'positive' | 'neutral' | 'warning'
}

export interface ClosingStep {
  order: number
  title: string
  detail: string
}

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

export const buildBuyerPersona = (
  lead: LeadResponse,
  summary: AdvisorSummaryResponse,
): BuyerPersona => {
  const affiliated = lead.afiliado === true
  const category = lead.categoria_afiliacion
  const savings = lead.ahorro ?? 0
  const householdIncome = lead.ingreso_hogar ?? lead.salario_mensual ?? 0
  const timeline = lead.plazo_compra ?? 'no_definido'
  const hasDependents = (lead.personas_a_cargo ?? 0) > 0
  const readinessScore = Number(summary.readiness?.score ?? 0)

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
      : timeline === '6_meses' || readinessScore >= 70
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
    readinessScore >= 70
      ? 'Perfil listo para cierre comercial: agenda visita o formaliza interés en el proyecto top.'
      : 'Todavía conviene nutrir el perfil, pero puedes dejar una opción ancla y un próximo paso.'

  return {
    title,
    segment,
    urgency,
    motivation,
    profileBullets,
    talkTracks,
    objections,
    closingAngle,
  }
}

export const buildCallInsights = (
  lead: LeadResponse,
  summary: AdvisorSummaryResponse,
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

  const score = Number(summary.readiness?.score ?? 0)
  insights.push({
    label: 'Preparación',
    value: `Score ${score} · ${String(summary.readiness?.status ?? 'sin estado')} · confianza ${String(summary.readiness?.confidence ?? '—')}`,
    tone: score >= 70 ? 'positive' : score >= 45 ? 'neutral' : 'warning',
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
        ? `Ancla la conversación en ${topProject.project_name} (${Math.round(topProject.compatibility_score)}% compatibilidad) y una alternativa.`
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
  return status.replaceAll('_', ' ')
}
