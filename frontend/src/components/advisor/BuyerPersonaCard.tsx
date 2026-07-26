import type { BuyerPersona } from '@/utils/advisorBriefing'
import { Badge } from '@/components/ui/Badge'

export const BuyerPersonaCard = ({ persona }: { persona: BuyerPersona }) => (
  <section className="rounded-[1.75rem] bg-white p-6 surface-shadow">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--color-green)]">
          Buyer persona
        </p>
        <h3 className="mt-2 font-display text-2xl text-[var(--color-ink)]">{persona.title}</h3>
        <p className="mt-1 text-sm text-[var(--color-muted)]">{persona.segment}</p>
      </div>
      <Badge
        className={
          persona.urgency === 'Alta'
            ? 'bg-[#c45c2a]'
            : persona.urgency === 'Media'
              ? 'bg-[var(--color-blue)]'
              : 'bg-[var(--color-muted)]'
        }
      >
        Urgencia {persona.urgency}
      </Badge>
    </div>
    <p className="mt-4 text-[var(--color-ink)]">{persona.motivation}</p>
    <ul className="mt-4 space-y-2 text-sm text-[var(--color-muted)]">
      {persona.profileBullets.map((item) => (
        <li key={item}>• {item}</li>
      ))}
    </ul>
    <div className="mt-5 rounded-2xl bg-[#f4f7fb] p-4">
      <p className="text-sm font-semibold text-[var(--color-blue)]">Ángulo de cierre</p>
      <p className="mt-1 text-sm text-[var(--color-ink)]">{persona.closingAngle}</p>
    </div>
    {persona.pptxHref && persona.pptxSlide != null && (
      <p className="mt-4 text-sm">
        <a
          href={persona.pptxHref}
          target="_blank"
          rel="noreferrer"
          className="font-semibold text-[var(--color-blue)] underline underline-offset-2 hover:opacity-80"
        >
          Ver en Buyer Person (diapositiva {persona.pptxSlide}
          {persona.projectName ? ` · ${persona.projectName}` : ''})
        </a>
      </p>
    )}
    {persona.projectName && !persona.historicalAvailable && !persona.pptxHref && (
      <p className="mt-4 text-sm text-[var(--color-muted)]">
        Sin buyer persona histórico para este proyecto.
      </p>
    )}
  </section>
)
