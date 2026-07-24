import type { LeadResponse } from '@/api/types'

const LABELS: Record<string, string> = {
  interesado: 'Interesado',
  indeciso: 'Indeciso',
  molesto: 'Molesto',
  trolleando: 'Solo respondiendo por molestar',
  ocupado: 'Ocupado / apurado',
  desconocido: 'Sin clasificar',
}

const TONES: Record<string, string> = {
  interesado: 'bg-[#e8f6ee] text-[#1f6b45] border-[#b7e0c8]',
  indeciso: 'bg-[#fff7e8] text-[#8a5a10] border-[#f0d7a4]',
  molesto: 'bg-[#fdeeee] text-[#8b2e2e] border-[#f0c2c2]',
  trolleando: 'bg-[#f3eef8] text-[#5b3d7a] border-[#d7c6ea]',
  ocupado: 'bg-[#eef3f8] text-[#2f4f6b] border-[#c5d5e6]',
  desconocido: 'bg-[#f4f3ef] text-[var(--color-muted)] border-[var(--color-line)]',
}

export const EngagementBadge = ({ lead }: { lead?: LeadResponse | null }) => {
  const label = (lead?.engagement_label as string | undefined) || null
  if (!label) return null
  const title = LABELS[label] ?? label
  const tone = TONES[label] ?? TONES.desconocido
  const score =
    typeof lead?.engagement_score === 'number' ? lead.engagement_score : null

  return (
    <div className={`rounded-2xl border px-4 py-3 text-left ${tone}`}>
      <p className="text-xs font-semibold uppercase tracking-[0.14em]">
        Predisposición (Laura)
      </p>
      <p className="mt-1 font-display text-xl">
        {title}
        {score !== null ? ` · ${score}/100` : ''}
      </p>
      {lead?.engagement_reason && (
        <p className="mt-1 text-sm opacity-90">{lead.engagement_reason}</p>
      )}
    </div>
  )
}
