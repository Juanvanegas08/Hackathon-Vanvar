import { Volume2, Square } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/Button'
import {
  buildLauraRecommendationScript,
  speakLauraText,
  stopLauraSpeech,
} from '@/utils/lauraSpeech'

export const LauraRecommendationSpeech = ({
  spokenSummary,
  brochureUrl,
  projectName,
  autoPlay = true,
}: {
  spokenSummary?: string | null
  brochureUrl?: string | null
  projectName?: string | null
  autoPlay?: boolean
}) => {
  const [speaking, setSpeaking] = useState(false)
  const [autoPlayBlocked, setAutoPlayBlocked] = useState(false)
  const playedRef = useRef(false)
  const stopRef = useRef<(() => void) | null>(null)

  const script = spokenSummary ? buildLauraRecommendationScript(spokenSummary) : ''

  const play = () => {
    if (!script) return
    stopRef.current?.()
    stopRef.current = speakLauraText(script, {
      onStart: () => {
        setSpeaking(true)
        setAutoPlayBlocked(false)
      },
      onEnd: () => setSpeaking(false),
      onError: () => {
        setSpeaking(false)
        setAutoPlayBlocked(true)
      },
    })
  }

  const stop = () => {
    stopRef.current?.()
    stopLauraSpeech()
    setSpeaking(false)
  }

  useEffect(() => {
    if (!autoPlay || !script || playedRef.current) return
    playedRef.current = true
    // Intento de autoplay; si el navegador lo bloquea, queda el botón.
    const timer = window.setTimeout(() => {
      try {
        play()
      } catch {
        setAutoPlayBlocked(true)
      }
    }, 600)
    return () => {
      window.clearTimeout(timer)
      stop()
    }
    // Solo al montar / cuando llega el summary.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [script, autoPlay])

  useEffect(() => () => stop(), [])

  if (!script) return null

  return (
    <div className="mb-6 rounded-3xl border border-[var(--color-line)] bg-white/90 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[var(--color-green)]">
            Recomendación de Laura
          </p>
          <p className="mt-1 text-sm text-[var(--color-muted)]">
            {speaking
              ? 'Laura te está contando la recomendación…'
              : autoPlayBlocked
                ? 'Pulsa el botón para escuchar a Laura.'
                : 'También puedes volver a escucharla cuando quieras.'}
          </p>
        </div>
        <div className="flex gap-2">
          {speaking ? (
            <Button variant="secondary" className="min-h-11" onClick={stop}>
              <Square className="mr-2 h-4 w-4" />
              Detener
            </Button>
          ) : (
            <Button className="min-h-11" onClick={play}>
              <Volume2 className="mr-2 h-4 w-4" />
              Escuchar a Laura
            </Button>
          )}
        </div>
      </div>

      <p className="mt-3 text-lg leading-relaxed text-[var(--color-ink)]">{script}</p>

      {brochureUrl && (
        <a
          href={brochureUrl}
          target="_blank"
          rel="noreferrer"
          className="mt-4 inline-flex text-sm font-semibold text-[var(--color-blue)] underline"
        >
          Abrir brochure{projectName ? ` de ${projectName}` : ''}
        </a>
      )}
    </div>
  )
}
