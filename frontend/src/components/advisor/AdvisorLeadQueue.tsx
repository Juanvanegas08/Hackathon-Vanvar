import type { LeadResponse } from '@/api/types'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import {
  affinityBandClass,
  isEvaluatedLead,
  resolveLeadAffinity,
  type AffinityBand,
} from '@/utils/advisorBriefing'
import { cn } from '@/utils/cn'

interface AdvisorLeadQueueProps {
  leads: LeadResponse[]
  selectedId: string | null
  onSelect: (leadId: string) => void
}

const queueBandLabel = (band?: AffinityBand | null): string => {
  if (band === 'listo') return 'Listo'
  if (band === 'por_evaluar') return 'Evaluar'
  if (band === 'baja_afinidad') return 'Baja'
  return '—'
}

export const AdvisorLeadQueue = ({
  leads,
  selectedId,
  onSelect,
}: AdvisorLeadQueueProps) => {
  const evaluatedLeads = leads.filter(isEvaluatedLead)

  return (
    <aside className="flex max-h-[min(28rem,70vh)] flex-col self-start rounded-[1.75rem] border border-[var(--color-line)] bg-white p-4 surface-shadow lg:sticky lg:top-4">
      <div className="mb-3 flex shrink-0 items-center justify-between gap-2">
        <h2 className="font-display text-xl">Cola de leads</h2>
        <Badge className="bg-[var(--color-green)]">{evaluatedLeads.length}</Badge>
      </div>
      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto overscroll-contain pr-1">
        {evaluatedLeads.map((lead) => {
          const active = lead.id === selectedId
          const { percent, band } = resolveLeadAffinity(lead)
          return (
            <button
              key={lead.id}
              type="button"
              onClick={() => onSelect(lead.id)}
              className={cn(
                'w-full rounded-2xl border px-3 py-3 text-left transition',
                active
                  ? 'border-[var(--color-yellow)] bg-[#fff9db]'
                  : 'border-[var(--color-line)] hover:border-[var(--color-yellow)]/70',
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <p className="min-w-0 flex-1 truncate font-semibold text-[var(--color-ink)]">
                  {lead.nombre ?? 'Lead sin nombre'}
                </p>
                <span
                  className={cn(
                    'shrink-0 whitespace-nowrap rounded-full px-2 py-0.5 text-[10px] font-bold uppercase',
                    affinityBandClass(band),
                  )}
                >
                  {queueBandLabel(band)}
                </span>
              </div>
              <p className="mt-1 text-xs text-[var(--color-muted)]">
                {lead.document_type ?? 'CC'} {lead.document_number ?? '—'}
              </p>
              <div className="mt-2 flex flex-wrap gap-1 text-[11px] text-[var(--color-muted)]">
                <span className="rounded-full bg-[#f1f0eb] px-2 py-0.5">
                  {lead.afiliado == null
                    ? 'Afil. ?'
                    : lead.afiliado
                      ? 'Afiliado'
                      : 'No afiliado'}
                </span>
                {lead.categoria_afiliacion && (
                  <span className="rounded-full bg-[#f1f0eb] px-2 py-0.5">
                    Cat. {lead.categoria_afiliacion}
                  </span>
                )}
                {percent != null && (
                  <span className="rounded-full bg-[#f1f0eb] px-2 py-0.5">
                    Afinidad {Math.round(percent)}%
                  </span>
                )}
              </div>
            </button>
          )
        })}
        {evaluatedLeads.length === 0 && (
          <p className="p-3 text-sm text-[var(--color-muted)]">
            No hay leads evaluados por Laura (web o llamada). Completa un perfil y
            genera recomendaciones para verlos aquí.
          </p>
        )}
      </div>
      {evaluatedLeads.length > 0 && !selectedId && (
        <Button className="mt-3 w-full shrink-0" onClick={() => onSelect(evaluatedLeads[0].id)}>
          Abrir primer lead
        </Button>
      )}
    </aside>
  )
}
