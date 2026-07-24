import type { CallInsight } from '@/utils/advisorBriefing'
import { cn } from '@/utils/cn'

const toneClass = {
  positive: 'border-l-[var(--color-green)] bg-[#f3faf6]',
  neutral: 'border-l-[var(--color-blue)] bg-[#f4f7fb]',
  warning: 'border-l-[#c45c2a] bg-[#fff6ef]',
} as const

export const CallInsightsCard = ({ insights }: { insights: CallInsight[] }) => (
  <section className="rounded-[1.75rem] bg-white p-6 surface-shadow">
    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--color-green)]">
      Lo identificado en la llamada
    </p>
    <h3 className="mt-2 font-display text-2xl">Hallazgos útiles para el cierre</h3>
    <div className="mt-5 space-y-3">
      {insights.map((item) => (
        <div
          key={item.label}
          className={cn('rounded-2xl border-l-4 px-4 py-3', toneClass[item.tone])}
        >
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-muted)]">
            {item.label}
          </p>
          <p className="mt-1 text-sm text-[var(--color-ink)]">{item.value}</p>
        </div>
      ))}
    </div>
  </section>
)
