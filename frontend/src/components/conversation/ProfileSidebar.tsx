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
  const overall =
    categories.reduce((acc, item) => acc + item.complete, 0) /
    Math.max(
      1,
      categories.reduce((acc, item) => acc + item.total, 0),
    )

  return (
    <aside className="overflow-hidden rounded-[2rem] border border-white/70 bg-white/80 p-6 text-left shadow-[0_20px_50px_rgba(30,58,95,0.08)] backdrop-blur-md">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--color-green)]">
        Armado de perfil
      </p>
      <h2 className="mt-1 font-display text-2xl">Tu perfil de vivienda</h2>

      <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-[#efeee9]">
        <div
          className="h-full rounded-full bg-gradient-to-r from-[var(--color-green)] to-[var(--color-yellow)] transition-all duration-500"
          style={{ width: `${Math.round(overall * 100)}%` }}
        />
      </div>
      <p className="mt-2 text-xs text-[var(--color-muted)]">
        {Math.round(overall * 100)}% completado
      </p>

      <div className="mt-4">
        <EngagementBadge lead={lead} />
      </div>

      {nextIncomplete && (
        <p className="mt-3 text-sm leading-relaxed text-[var(--color-muted)]">
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
              <div className="mb-1.5 flex justify-between text-sm">
                <span className="font-medium text-[var(--color-ink)]">{category.label}</span>
                <span className="text-[var(--color-muted)]">{state}</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-[#efeee9]">
                <div
                  className="h-full rounded-full bg-[var(--color-green)] transition-all duration-500"
                  style={{ width: `${ratio * 100}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>

      <button
        type="button"
        className="mt-6 flex w-full items-center justify-between rounded-2xl bg-[#f7f6f2] px-4 py-3 text-left text-sm font-semibold text-[var(--color-blue)] transition hover:bg-[#f1f0eb]"
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
