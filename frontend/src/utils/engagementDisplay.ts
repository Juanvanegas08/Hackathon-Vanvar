/** Shared sentiment UI for advisor briefing, badges and closing playbook. */

import type { LucideIcon } from 'lucide-react'
import {
  AlertTriangle,
  Angry,
  CircleHelp,
  Clock3,
  Frown,
  Handshake,
  HelpCircle,
  Meh,
  MessageSquareWarning,
  PartyPopper,
  Sparkles,
  Theater,
} from 'lucide-react'

export type EngagementTone = 'positive' | 'neutral' | 'warning'

export type EngagementLabel =
  | 'feliz'
  | 'triste'
  | 'enojado'
  | 'consternado'
  | 'grosero'
  | 'cortes'
  | 'interesado'
  | 'indeciso'
  | 'molesto'
  | 'trolleando'
  | 'ocupado'
  | 'desconocido'

export const ENGAGEMENT_LABELS = [
  'feliz',
  'triste',
  'enojado',
  'consternado',
  'grosero',
  'cortes',
  'interesado',
  'indeciso',
  'molesto',
  'trolleando',
  'ocupado',
  'desconocido',
] as const satisfies readonly EngagementLabel[]

type EngagementDisplay = {
  title: string
  Icon: LucideIcon
  tone: EngagementTone
  badgeClass: string
  guidance: string[]
}

const DISPLAY: Record<EngagementLabel, EngagementDisplay> = {
  feliz: {
    title: 'Feliz',
    Icon: PartyPopper,
    tone: 'positive',
    badgeClass: 'bg-[#e8f6ee] text-[#1f6b45] border-[#b7e0c8]',
    guidance: [
      'Aprovecha el buen ánimo: ve directo a 1–2 proyectos ancla.',
      'Confirma disponibilidad y agenda visita o seguimiento en 24–48h.',
      'Mantén el tono cercano y celebra el avance sin alargar.',
    ],
  },
  triste: {
    title: 'Triste',
    Icon: Frown,
    tone: 'warning',
    badgeClass: 'bg-[#eef3f8] text-[#2f4f6b] border-[#c5d5e6]',
    guidance: [
      'Empieza con empatía; no apresures la venta.',
      'Habla con calma de opciones realistas y pasos pequeños.',
      'Ofrece apoyo y un siguiente paso suave (brochure o callback).',
    ],
  },
  enojado: {
    title: 'Enojado',
    Icon: Angry,
    tone: 'warning',
    badgeClass: 'bg-[#fdeeee] text-[#8b2e2e] border-[#f0c2c2]',
    guidance: [
      'Empieza con empatía y pide permiso para continuar.',
      'Acorta la llamada: solo lo esencial y una opción clara.',
      'Si persiste el malestar, ofrece retomar en otro momento.',
    ],
  },
  consternado: {
    title: 'Consternado',
    Icon: AlertTriangle,
    tone: 'warning',
    badgeClass: 'bg-[#fff7e8] text-[#8a5a10] border-[#f0d7a4]',
    guidance: [
      'Baja la presión y aclara dudas con paciencia.',
      'Explica en lenguaje simple precios, plazos y requisitos.',
      'Cierra con una decisión pequeña y tranquilizadora.',
    ],
  },
  grosero: {
    title: 'Grosero',
    Icon: MessageSquareWarning,
    tone: 'warning',
    badgeClass: 'bg-[#fdeeee] text-[#8b2e2e] border-[#f0c2c2]',
    guidance: [
      'Mantén límites firmes y tono profesional sin confrontar.',
      'No profundices datos sensibles si no hay respeto mutuo.',
      'Documenta el tono y prioriza otros leads si no hay interés real.',
    ],
  },
  cortes: {
    title: 'Cortés',
    Icon: Handshake,
    tone: 'positive',
    badgeClass: 'bg-[#e8f6ee] text-[#1f6b45] border-[#b7e0c8]',
    guidance: [
      'Reciprocidad: sé igual de claro y amable.',
      'Puedes profundizar un poco más en opciones y siguientes pasos.',
      'Agradece el trato y confirma el compromiso de seguimiento.',
    ],
  },
  interesado: {
    title: 'Interesado',
    Icon: Sparkles,
    tone: 'positive',
    badgeClass: 'bg-[#e8f6ee] text-[#1f6b45] border-[#b7e0c8]',
    guidance: [
      'Aprovecha el momentum: ve directo a 1–2 proyectos ancla.',
      'Confirma disponibilidad y agenda visita o seguimiento en 24–48h.',
      'Refuerza beneficios concretos sin alargar la explicación.',
    ],
  },
  indeciso: {
    title: 'Indeciso',
    Icon: HelpCircle,
    tone: 'neutral',
    badgeClass: 'bg-[#fff7e8] text-[#8a5a10] border-[#f0d7a4]',
    guidance: [
      'Baja la presión y aclara dudas de precio, plazo y ubicación.',
      'Compara máximo 2 opciones con pros concretos.',
      'Cierra con una decisión pequeña (brochure, visita o callback).',
    ],
  },
  molesto: {
    title: 'Molesto',
    Icon: Meh,
    tone: 'warning',
    badgeClass: 'bg-[#fdeeee] text-[#8b2e2e] border-[#f0c2c2]',
    guidance: [
      'Empieza con empatía y pide permiso para continuar.',
      'Acorta la llamada: solo lo esencial del perfil y una opción.',
      'Si persiste el malestar, ofrece retomar en otro momento.',
    ],
  },
  trolleando: {
    title: 'Solo por molestar',
    Icon: Theater,
    tone: 'warning',
    badgeClass: 'bg-[#f3eef8] text-[#5b3d7a] border-[#d7c6ea]',
    guidance: [
      'Valida si hay interés real con una pregunta cerrada.',
      'No profundices datos sensibles si no hay seriedad.',
      'Documenta el tono y prioriza otros leads de la cola.',
    ],
  },
  ocupado: {
    title: 'Ocupado / apurado',
    Icon: Clock3,
    tone: 'neutral',
    badgeClass: 'bg-[#eef3f8] text-[#2f4f6b] border-[#c5d5e6]',
    guidance: [
      'Sé breve y ofrece retomar en un horario concreto.',
      'Deja un mensaje con el proyecto top y el siguiente paso.',
      'Agenda callback en lugar de forzar el cierre ahora.',
    ],
  },
  desconocido: {
    title: 'Sin clasificar',
    Icon: CircleHelp,
    tone: 'neutral',
    badgeClass: 'bg-[#f4f3ef] text-[var(--color-muted)] border-[var(--color-line)]',
    guidance: [
      'Explora el tono con una pregunta abierta corta.',
      'Confirma motivación y urgencia antes de vender.',
      'Usa el perfil financiero/ubicación como ancla de conversación.',
    ],
  },
}

const DEFAULT_GUIDANCE = [
  'Laura aún no reportó sentimiento para este lead.',
  'Revisa la conversación y confirma interés al contacto.',
  'Puedes completar el perfil y volver a evaluar.',
]

export const resolveEngagementDisplay = (
  label?: string | null,
): EngagementDisplay & {
  label: string | null
  headline: string
} => {
  if (!label) {
    return {
      label: null,
      title: 'Sin sentimiento registrado',
      Icon: CircleHelp,
      tone: 'neutral',
      badgeClass: DISPLAY.desconocido.badgeClass,
      guidance: DEFAULT_GUIDANCE,
      headline: 'Sin sentimiento registrado',
    }
  }
  const key = label as EngagementLabel
  const item = DISPLAY[key] ?? {
    title: label,
    Icon: CircleHelp,
    tone: 'neutral' as const,
    badgeClass: DISPLAY.desconocido.badgeClass,
    guidance: DISPLAY.desconocido.guidance,
  }
  return {
    label,
    ...item,
    headline: item.title,
  }
}
