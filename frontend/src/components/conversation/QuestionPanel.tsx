import type { NextQuestion } from '@/api/types'
import { AnswerControls } from '@/components/conversation/AnswerControls'

interface QuestionPanelProps {
  question: NextQuestion
  onAnswer: (answer: string | boolean | number) => void
  disabled?: boolean
}

export const QuestionPanel = ({ question, onAnswer, disabled }: QuestionPanelProps) => (
  <section className="rounded-[2rem] bg-white p-7 text-left surface-shadow sm:p-10">
    <p className="mb-3 text-sm font-semibold uppercase tracking-wider text-[var(--color-green)]">
      Laura te escucha
    </p>
    <h1 className="font-display text-3xl leading-tight text-[var(--color-ink)] sm:text-5xl">
      {question.question}
    </h1>
    {question.reason && (
      <p className="mt-4 text-[var(--color-muted)]">{question.reason}</p>
    )}
    <div className="mt-8">
      <AnswerControls question={question} onAnswer={onAnswer} disabled={disabled} />
    </div>
  </section>
)
