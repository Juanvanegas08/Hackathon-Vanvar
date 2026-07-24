import type { ClosingStep } from '@/utils/advisorBriefing'

export const ClosingPlaybookCard = ({
  steps,
  talkTracks,
  objections,
}: {
  steps: ClosingStep[]
  talkTracks: string[]
  objections: string[]
}) => (
  <section className="rounded-[1.75rem] bg-[var(--color-blue)] p-6 text-white shadow-xl">
    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--color-yellow-soft)]">
      Guión de cierre
    </p>
    <h3 className="mt-2 font-display text-2xl">Orquestación para el asesor humano</h3>
    <ol className="mt-5 space-y-3">
      {steps.map((step) => (
        <li key={step.order} className="rounded-2xl bg-white/10 p-4">
          <p className="text-sm font-bold text-[var(--color-yellow-soft)]">
            Paso {step.order}. {step.title}
          </p>
          <p className="mt-1 text-sm text-white/90">{step.detail}</p>
        </li>
      ))}
    </ol>
    <div className="mt-5 grid gap-4 md:grid-cols-2">
      <div>
        <p className="text-sm font-semibold text-[var(--color-yellow-soft)]">Cómo hablarle</p>
        <ul className="mt-2 space-y-2 text-sm text-white/90">
          {talkTracks.map((item) => (
            <li key={item}>• {item}</li>
          ))}
        </ul>
      </div>
      <div>
        <p className="text-sm font-semibold text-[var(--color-yellow-soft)]">Objeciones probables</p>
        <ul className="mt-2 space-y-2 text-sm text-white/90">
          {objections.map((item) => (
            <li key={item}>• {item}</li>
          ))}
        </ul>
      </div>
    </div>
  </section>
)
