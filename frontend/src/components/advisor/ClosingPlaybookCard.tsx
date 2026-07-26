import type { LeadResponse } from '@/api/types'
import { resolveEngagementDisplay } from '@/utils/engagementDisplay'

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
  const display = resolveEngagementDisplay(label)
  const Icon = display.Icon
  const score =
    typeof lead.engagement_score === 'number' ? lead.engagement_score : null
  const updatedAt = formatUpdatedAt(lead.engagement_updated_at as string | null | undefined)

  return (
    <section className="rounded-[1.75rem] bg-[var(--color-blue)] p-6 text-white shadow-xl">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--color-yellow-soft)]">
        Sentimiento detectado
      </p>
      <h3 className="mt-2 font-display text-2xl">Cómo se sintió la persona</h3>
      <p className="mt-2 max-w-2xl text-sm text-white/85">
        Lectura de Laura sobre emoción, tono e interés durante la llamada o conversación.
      </p>

      <div className="mt-5 grid gap-4 md:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        <div className="rounded-2xl bg-white/10 p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--color-yellow-soft)]">
            Resultado
          </p>
          <div className="mt-3 flex items-center gap-3">
            <span className="grid h-12 w-12 place-items-center rounded-2xl bg-white/15 text-[var(--color-yellow-soft)]">
              <Icon size={26} strokeWidth={1.75} aria-hidden />
            </span>
            <p className="font-display text-3xl md:text-4xl">{display.title}</p>
          </div>
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
            {display.guidance.map((item) => (
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
