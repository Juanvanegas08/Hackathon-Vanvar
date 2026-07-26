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

/** Organic morph keyframes — feels like a living voice blob while speaking. */
const speakMorph = [
  '42% 58% 48% 52% / 48% 42% 58% 52%',
  '58% 42% 55% 45% / 42% 58% 42% 58%',
  '48% 52% 42% 58% / 55% 45% 52% 48%',
  '55% 45% 58% 42% / 45% 55% 48% 52%',
  '42% 58% 48% 52% / 48% 42% 58% 52%',
]

const listenMorph = [
  '50% 50% 50% 50% / 50% 50% 50% 50%',
  '48% 52% 52% 48% / 52% 48% 48% 52%',
  '50% 50% 50% 50% / 50% 50% 50% 50%',
]

export const VoiceOrb = ({
  state,
  onClick,
  intensity = 0,
}: {
  state: VoiceState
  onClick?: () => void
  /** 0–1 voice energy hint (speaking sync). */
  intensity?: number
}) => {
  const reduceMotion = useReducedMotion()
  const speaking = state === 'speaking'
  const listening = state === 'listening'
  const pulse = speaking || listening
  const think = state === 'thinking' || state === 'confirming' || state === 'connecting'
  const interactive = Boolean(onClick) && (speaking || listening)
  const energy = speaking ? Math.min(1, Math.max(0.35, intensity || 0.65)) : listening ? 0.25 : 0

  return (
    <div className="relative mx-auto grid place-items-center py-4">
      {!reduceMotion && pulse && (
        <>
          <motion.span
            className="absolute h-52 w-52 rounded-full border border-[var(--color-yellow)]/40"
            animate={{
              scale: [1, speaking ? 1.28 + energy * 0.2 : 1.18, 1],
              opacity: [0.5, 0, 0.5],
            }}
            transition={{ duration: speaking ? 1.1 : 2.2, repeat: Infinity, ease: 'easeOut' }}
          />
          <motion.span
            className="absolute h-52 w-52 rounded-full border border-[var(--color-blue)]/25"
            animate={{
              scale: [1, speaking ? 1.45 + energy * 0.25 : 1.32, 1],
              opacity: [0.35, 0, 0.35],
            }}
            transition={{
              duration: speaking ? 1.4 : 2.6,
              repeat: Infinity,
              ease: 'easeOut',
              delay: 0.2,
            }}
          />
        </>
      )}

      <motion.button
        type="button"
        aria-label={
          speaking ? 'Interrumpir al asistente' : 'Estado del asistente de voz'
        }
        disabled={!interactive}
        onClick={onClick}
        animate={
          reduceMotion || state === 'error'
            ? undefined
            : speaking
              ? {
                  borderRadius: speakMorph,
                  scale: [1, 1.05 + energy * 0.12, 0.96, 1.08 + energy * 0.08, 1],
                  rotate: [0, 4, -3, 2, 0],
                  x: [0, 3, -4, 2, 0],
                  y: [0, -4, 2, -3, 0],
                }
              : listening
                ? {
                    borderRadius: listenMorph,
                    scale: [1, 1.03, 1],
                  }
                : think
                  ? { rotate: [0, 10, -10, 0], scale: [1, 0.94, 1] }
                  : state === 'completed'
                    ? { scale: [1, 1.08, 1] }
                    : { scale: 1, borderRadius: '50%' }
        }
        transition={{
          duration: speaking ? 1.35 : think ? 2.4 : 2,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
        className={cn(
          'relative grid h-40 w-40 place-items-center shadow-[0_20px_60px_rgba(30,58,95,0.35)]',
          'overflow-hidden',
          state === 'error'
            ? 'bg-[radial-gradient(circle_at_30%_25%,#f8d7da_0%,#c45c5c_55%,#1e3a5f_100%)]'
            : 'bg-[radial-gradient(circle_at_28%_22%,#fff9d0_0%,#f5c518_38%,#2a5080_78%,#152a45_100%)]',
          interactive && 'cursor-pointer',
        )}
        style={{ borderRadius: '50%' }}
      >
        <motion.div
          className="absolute inset-0 bg-[radial-gradient(circle_at_70%_80%,rgba(255,255,255,0.22),transparent_55%)]"
          animate={
            speaking && !reduceMotion
              ? { opacity: [0.4, 0.85, 0.35, 0.7, 0.4], scale: [1, 1.08, 0.96, 1.05, 1] }
              : { opacity: 0.5 }
          }
          transition={{ duration: 1.1, repeat: Infinity, ease: 'easeInOut' }}
        />
        <div className="relative h-14 w-14 rounded-full bg-white/30 shadow-inner backdrop-blur-md" />
      </motion.button>

      <p className="mt-5 text-xs font-semibold uppercase tracking-[0.22em] text-[var(--color-muted)]">
        {stateLabel[state]}
      </p>
    </div>
  )
}
