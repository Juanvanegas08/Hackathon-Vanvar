import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import type { LeadResponse } from '@/api/types'
import { DetectedFacts } from '@/components/conversation/DetectedFacts'
import { EngagementBadge } from '@/components/conversation/EngagementBadge'
import { getProfileProgress } from '@/utils/profileProgress'

const messages: Record<string, string> = {
  affiliation: 'Ya entendimos tu situación de afiliación.',
  household: 'Estamos conociendo tu hogar.',
  capacity: 'Estamos afinando tu capacidad orientativa.',
  preferences: 'Solo falta conocer dónde te gustaría vivir.',
}

export const ProfileSidebar = ({ lead }: { lead?: LeadResponse | null }) => {
  const [open, setOpen] = useState(false)
  const categories = getProfileProgress(lead)
  const nextIncomplete = categories.find((item) => item.complete < item.total)

  return (
    <aside className="rounded-3xl border border-[var(--color-line)] bg-white p-5 text-left">
      <h2 className="font-display text-xl">Tu perfil de vivienda</h2>
      <div className="mt-4">
        <EngagementBadge lead={lead} />
      </div>
      {nextIncomplete && (
        <p className="mt-2 text-sm text-[var(--color-muted)]">
          {messages[nextIncomplete.key] ?? 'Seguimos avanzando juntos.'}
        </p>
      )}

      <div className="mt-5 space-y-4">
        {categories.map((category) => {
          const ratio = category.total === 0 ? 0 : category.complete / category.total
          const state =
            ratio === 1 ? 'Completado' : ratio > 0 ? 'En progreso' : 'Pendiente'
          return (
            <div key={category.key}>
              <div className="mb-1 flex justify-between text-sm">
                <span>{category.label}</span>
                <span className="text-[var(--color-muted)]">{state}</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-[#efeee9]">
                <div
                  className="h-full rounded-full bg-[var(--color-green)] transition-all"
                  style={{ width: `${ratio * 100}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>

      <button
        type="button"
        className="mt-6 flex w-full items-center justify-between text-left font-semibold text-[var(--color-blue)]"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
      >
        Lo que hemos entendido
        <ChevronDown
          className={open ? 'rotate-180 transition-transform' : 'transition-transform'}
          size={18}
          aria-hidden
        />
      </button>
      {open && lead && (
        <div className="mt-3">
          <DetectedFacts lead={lead} />
        </div>
      )}
    </aside>
  )
}
