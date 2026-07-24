import type { LeadResponse } from '@/api/types'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { formatStatus } from '@/utils/advisorBriefing'
import { cn } from '@/utils/cn'

interface AdvisorLeadQueueProps {
  leads: LeadResponse[]
  selectedId: string | null
  onSelect: (leadId: string) => void
}

export const AdvisorLeadQueue = ({
  leads,
  selectedId,
  onSelect,
}: AdvisorLeadQueueProps) => (
  <aside className="rounded-[1.75rem] border border-[var(--color-line)] bg-white p-4 surface-shadow">
    <div className="mb-4 flex items-center justify-between gap-2">
      <h2 className="font-display text-xl">Cola de leads</h2>
      <Badge className="bg-[var(--color-green)]">{leads.length}</Badge>
    </div>
    <div className="max-h-[70vh] space-y-2 overflow-y-auto pr-1">
      {leads.map((lead) => {
        const active = lead.id === selectedId
        const scoreReady =
          lead.estado_lead === 'listo_para_asesor' || lead.status === 'listo_para_asesor'
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
              <p className="font-semibold text-[var(--color-ink)]">
                {lead.nombre ?? 'Lead sin nombre'}
              </p>
              {scoreReady && (
                <span className="rounded-full bg-[var(--color-green)] px-2 py-0.5 text-[10px] font-bold uppercase text-white">
                  Listo
                </span>
              )}
            </div>
            <p className="mt-1 text-xs text-[var(--color-muted)]">
              {lead.document_type ?? 'CC'} {lead.document_number ?? '—'}
            </p>
            <div className="mt-2 flex flex-wrap gap-1 text-[11px] text-[var(--color-muted)]">
              <span className="rounded-full bg-[#f1f0eb] px-2 py-0.5">
                {lead.afiliado == null ? 'Afil. ?' : lead.afiliado ? 'Afiliado' : 'No afiliado'}
              </span>
              {lead.categoria_afiliacion && (
                <span className="rounded-full bg-[#f1f0eb] px-2 py-0.5">
                  Cat. {lead.categoria_afiliacion}
                </span>
              )}
              <span className="rounded-full bg-[#f1f0eb] px-2 py-0.5">
                {formatStatus(lead.estado_lead ?? lead.status)}
              </span>
            </div>
          </button>
        )
      })}
      {leads.length === 0 && (
        <p className="p-3 text-sm text-[var(--color-muted)]">
          No hay leads en memoria. Corre un escenario demo y vuelve aquí.
        </p>
      )}
    </div>
    {leads.length > 0 && !selectedId && (
      <Button className="mt-4 w-full" onClick={() => onSelect(leads[0].id)}>
        Abrir primer lead
      </Button>
    )}
  </aside>
)
