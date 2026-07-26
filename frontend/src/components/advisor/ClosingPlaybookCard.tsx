import type { LeadResponse } from '@/api/types'

const LABELS: Record<string, string> = {
  interesado: 'Interesado',
  indeciso: 'Indeciso',
  molesto: 'Molesto',
  trolleando: 'Solo respondiendo por molestar',
  ocupado: 'Ocupado / apurado',
  desconocido: 'Sin clasificar',
}

const ADVISOR_GUIDANCE: Record<string, string[]> = {
  interesado: [
    'Aprovecha el momentum: ve directo a 1–2 proyectos ancla.',
    'Confirma disponibilidad y agenda visita o seguimiento en 24–48h.',
    'Refuerza beneficios concretos sin alargar la explicación.',
  ],
  indeciso: [
    'Baja la presión y aclara dudas de precio, plazo y ubicación.',
    'Compara máximo 2 opciones con pros concretos.',
    'Cierra con una decisión pequeña (brochure, visita o callback).',
  ],
  molesto: [
    'Empieza con empatía y pide permiso para continuar.',
    'Acorta la llamada: solo lo esencial del perfil y una opción.',
    'Si persiste el malestar, ofrece retomar en otro momento.',
  ],
  trolleando: [
    'Valida si hay interés real con una pregunta cerrada.',
    'No profundices datos sensibles si no hay seriedad.',
    'Documenta el tono y prioriza otros leads de la cola.',
  ],
  ocupado: [
    'Sé breve y ofrece retomar en un horario concreto.',
    'Deja un mensaje con el proyecto top y el siguiente paso.',
    'Agenda callback en lugar de forzar el cierre ahora.',
  ],
  desconocido: [
    'Explora el tono con una pregunta abierta corta.',
    'Confirma motivación y urgencia antes de vender.',
    'Usa el perfil financiero/ubicación como ancla de conversación.',
  ],
}

const formatUpdatedAt = (value?: string | null): string | null => {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  return date.toLocaleString('es-CO', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

export const ClosingPlaybookCard = ({ lead }: { lead: LeadResponse }) => {
  const label = (lead.engagement_label as string | undefined) || null
  const title = label ? (LABELS[label] ?? label) : 'Sin predisposición registrada'
  const score =
    typeof lead.engagement_score === 'number' ? lead.engagement_score : null
  const guidance = label
    ? (ADVISOR_GUIDANCE[label] ?? ADVISOR_GUIDANCE.desconocido)
    : [
        'Laura aún no reportó sentimiento para este lead.',
        'Revisa la conversación y confirma interés al contacto.',
        'Puedes completar el perfil y volver a evaluar.',
      ]
  const updatedAt = formatUpdatedAt(lead.engagement_updated_at as string | null | undefined)

  return (
    <section className="rounded-[1.75rem] bg-[var(--color-blue)] p-6 text-white shadow-xl">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--color-yellow-soft)]">
        Sentimiento detectado
      </p>
      <h3 className="mt-2 font-display text-2xl">Predisposición de la persona</h3>
      <p className="mt-2 max-w-2xl text-sm text-white/85">
        Lectura de Laura sobre el tono e interés durante la conversación.
      </p>

      <div className="mt-5 grid gap-4 md:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        <div className="rounded-2xl bg-white/10 p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--color-yellow-soft)]">
            Resultado
          </p>
          <p className="mt-2 font-display text-3xl md:text-4xl">{title}</p>
          {score !== null && (
            <p className="mt-3 text-lg font-semibold text-[var(--color-yellow-soft)]">
              Intensidad {score}/100
            </p>
          )}
          {lead.engagement_reason ? (
            <p className="mt-3 text-sm leading-relaxed text-white/90">
              {lead.engagement_reason}
            </p>
          ) : (
            <p className="mt-3 text-sm text-white/70">
              Sin detalle adicional del motivo.
            </p>
          )}
          {updatedAt && (
            <p className="mt-4 text-xs text-white/65">Actualizado: {updatedAt}</p>
          )}
        </div>

        <div className="rounded-2xl bg-white/10 p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--color-yellow-soft)]">
            Cómo abordarlo
          </p>
          <ul className="mt-3 space-y-3 text-sm text-white/90">
            {guidance.map((item) => (
              <li key={item} className="flex gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--color-yellow-soft)]" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}
