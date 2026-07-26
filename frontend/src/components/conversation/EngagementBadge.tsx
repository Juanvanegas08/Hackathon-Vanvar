import type { LeadResponse } from '@/api/types'
import { resolveEngagementDisplay } from '@/utils/engagementDisplay'

export const EngagementBadge = ({ lead }: { lead?: LeadResponse | null }) => {
  const label = (lead?.engagement_label as string | undefined) || null
  if (!label) return null
  const display = resolveEngagementDisplay(label)
  const Icon = display.Icon
  const score =
    typeof lead?.engagement_score === 'number' ? lead.engagement_score : null

  return (
    <div className={`rounded-2xl border px-4 py-3 text-left ${display.badgeClass}`}>
      <p className="text-xs font-semibold uppercase tracking-[0.14em]">
        Sentimiento (Laura)
      </p>
      <p className="mt-1 flex items-center gap-2 font-display text-xl">
        <Icon size={20} strokeWidth={1.75} aria-hidden className="shrink-0 opacity-90" />
        <span>
          {display.title}
          {score !== null ? ` · ${score}/100` : ''}
        </span>
      </p>
      {lead?.engagement_reason && (
        <p className="mt-1 text-sm opacity-90">{lead.engagement_reason}</p>
      )}
    </div>
  )
}
