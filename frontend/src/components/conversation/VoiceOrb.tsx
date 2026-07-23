import { motion, useReducedMotion } from 'framer-motion'
import type { VoiceState } from '@/providers/voiceTypes'
import { cn } from '@/utils/cn'

const stateLabel: Record<VoiceState, string> = {
  idle: 'Listo',
  connecting: 'Conectando',
  listening: 'Escuchando',
  thinking: 'Procesando',
  speaking: 'Hablando',
  confirming: 'Esperando confirmación',
  completed: 'Listo',
  error: 'Error',
}

export const VoiceOrb = ({
  state,
  onClick,
}: {
  state: VoiceState
  onClick?: () => void
}) => {
  const reduceMotion = useReducedMotion()
  const pulse = state === 'listening' || state === 'speaking'
  const think = state === 'thinking' || state === 'confirming' || state === 'connecting'
  const interactive = Boolean(onClick) && (state === 'speaking' || state === 'listening')

  return (
    <div className="relative mx-auto grid place-items-center">
      {!reduceMotion && pulse && (
        <>
          <motion.span
            className="absolute h-44 w-44 rounded-full border border-[var(--color-yellow)]/50"
            animate={{ scale: [1, state === 'speaking' ? 1.35 : 1.25], opacity: [0.55, 0] }}
            transition={{ duration: 1.8, repeat: Infinity }}
          />
          <motion.span
            className="absolute h-44 w-44 rounded-full border border-[var(--color-yellow)]/30"
            animate={{ scale: [1, state === 'speaking' ? 1.55 : 1.45], opacity: [0.4, 0] }}
            transition={{ duration: 1.8, repeat: Infinity, delay: 0.35 }}
          />
        </>
      )}
      <motion.button
        type="button"
        aria-label={
          state === 'speaking' ? 'Interrumpir al asistente' : 'Estado del asistente de voz'
        }
        disabled={!interactive}
        onClick={onClick}
        animate={
          reduceMotion || state === 'error'
            ? undefined
            : think
              ? { rotate: [0, 8, -8, 0], scale: [1, 0.96, 1] }
              : pulse
                ? { scale: [1, 1.06, 1] }
                : state === 'completed'
                  ? { scale: [1, 1.08, 1] }
                  : { scale: 1 }
        }
        transition={{ duration: think ? 2.4 : 1.6, repeat: Infinity, ease: 'easeInOut' }}
        className={cn(
          'relative grid h-36 w-36 place-items-center rounded-full shadow-2xl',
          state === 'error'
            ? 'bg-[radial-gradient(circle_at_30%_25%,#f8d7da_0%,#c45c5c_55%,#1e3a5f_100%)]'
            : 'bg-[radial-gradient(circle_at_30%_25%,#fff6b8_0%,#f5c518_42%,#1e3a5f_100%)]',
          interactive && 'cursor-pointer',
        )}
      >
        <div className="h-16 w-16 rounded-full bg-white/25 backdrop-blur-sm" />
      </motion.button>
      <p className="mt-4 text-sm font-semibold uppercase tracking-[0.18em] text-[var(--color-muted)]">
        {stateLabel[state]}
      </p>
    </div>
  )
}
