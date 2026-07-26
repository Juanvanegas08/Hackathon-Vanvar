import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Mic, MicOff, PhoneOff, VolumeX } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getLead } from '@/api/leads.api'
import { ProfileSidebar } from '@/components/conversation/ProfileSidebar'
import { VoiceOrb } from '@/components/conversation/VoiceOrb'
import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/Button'
import { ErrorState } from '@/components/ui/ErrorState'
import { Spinner } from '@/components/ui/Spinner'
import { useVoiceSession } from '@/providers/VoiceSessionProvider'
import { setSessionLeadId } from '@/utils/session'

export const ConversationPage = () => {
  const { leadId = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const {
    voiceState,
    startSession,
    stopSession,
    providerName,
    isConnected,
    isMuted,
    toggleMute,
    interrupt,
    error: voiceError,
    retry,
  } = useVoiceSession()

  const [error, setError] = useState<string | null>(null)
  const [orbIntensity, setOrbIntensity] = useState(0.55)

  const useRealtimeVoice = providerName === 'openai'

  useEffect(() => {
    if (leadId) setSessionLeadId(leadId)
  }, [leadId])

  // El provider de voz es global: al salir de esta sección hay que apagar
  // micrófono + WebRTC. Si no, Laura sigue viva en otras rutas.
  useEffect(() => {
    return () => {
      void stopSession()
    }
  }, [leadId, stopSession])

  useEffect(() => {
    const handler = () => {
      void queryClient.invalidateQueries({ queryKey: ['lead', leadId] })
    }
    window.addEventListener('casalista-engagement-updated', handler)
    return () => window.removeEventListener('casalista-engagement-updated', handler)
  }, [leadId, queryClient])

  useEffect(() => {
    const handler = (path: string) => {
      navigate(path)
    }
    window.dispatchEvent(new CustomEvent('casalista-voice-navigate', { detail: handler }))
  }, [navigate])

  const leadQuery = useQuery({
    queryKey: ['lead', leadId],
    queryFn: () => getLead(leadId),
    enabled: Boolean(leadId),
    retry: false,
  })

  // Sync orb deformation with speaking state (organic pulse while Laura talks).
  useEffect(() => {
    if (voiceState !== 'speaking') {
      setOrbIntensity(0.2)
      return
    }
    let frame = 0
    const timer = window.setInterval(() => {
      frame += 1
      const wave =
        0.45 +
        0.35 * Math.sin(frame / 3.2) +
        0.2 * Math.sin(frame / 1.7) +
        0.12 * Math.sin(frame / 0.9)
      setOrbIntensity(Math.min(1, Math.max(0.35, wave)))
    }, 90)
    return () => window.clearInterval(timer)
  }, [voiceState])

  useEffect(() => {
    if (!useRealtimeVoice || !isConnected || !leadId) return
    const onLeadUpdated = () => {
      void queryClient.invalidateQueries({ queryKey: ['lead', leadId] })
    }
    window.addEventListener('casalista-lead-updated', onLeadUpdated)
    const timer = window.setInterval(onLeadUpdated, 12_000)
    return () => {
      window.removeEventListener('casalista-lead-updated', onLeadUpdated)
      window.clearInterval(timer)
    }
  }, [isConnected, leadId, queryClient, useRealtimeVoice])

  useEffect(() => {
    if (!leadQuery.isError) return
    const status = (leadQuery.error as { status?: number } | null)?.status
    if (status === 404) {
      void stopSession()
    }
  }, [leadQuery.error, leadQuery.isError, stopSession])

  // El micrófono exige un clic del usuario: no autoiniciar.
  // Se arranca solo con "Iniciar conversación".

  if (leadQuery.isLoading) {
    return (
      <AppShell>
        <div className="grid min-h-[60vh] place-items-center">
          <Spinner label="Preparando tu conversación" />
        </div>
      </AppShell>
    )
  }

  if (leadQuery.isError) {
    const status = (leadQuery.error as { status?: number } | null)?.status
    if (status === 404 || status === 422) {
      const message =
        status === 422
          ? 'Hubo un problema al actualizar tu perfil. Empecemos de nuevo.'
          : 'La sesión ya no está disponible. Podemos comenzar una nueva.'
      return (
        <AppShell>
          <div className="mx-auto max-w-lg py-16">
            <ErrorState message={message} onRetry={() => navigate('/identification')} />
            <Link to="/" className="mt-4 inline-block text-[var(--color-blue)] hover:underline">
              Ir al inicio
            </Link>
          </div>
        </AppShell>
      )
    }
  }

  const statusHint =
    voiceState === 'connecting'
      ? 'Conectando con Laura…'
      : voiceState === 'speaking'
        ? 'Laura está hablando. Toca el orbe o habla para interrumpir.'
        : voiceState === 'listening'
          ? 'Te escucha. Habla con naturalidad.'
          : voiceState === 'thinking'
            ? 'Un momento, Laura está procesando…'
            : 'Conversación por voz con Laura'

  return (
    <AppShell>
      <div className="relative py-4 lg:py-8">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 -top-8 h-72 bg-[radial-gradient(ellipse_at_50%_0%,rgba(245,197,24,0.18),transparent_60%)]"
        />

        <div className="relative grid gap-8 lg:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.8fr)] lg:items-start">
          <section className="flex flex-col items-center text-center">
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="w-full max-w-xl rounded-[2rem] border border-white/60 bg-white/55 px-6 py-10 shadow-[0_24px_80px_rgba(30,58,95,0.08)] backdrop-blur-md sm:px-10"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--color-green)]">
                Laura · voz
              </p>
              <h1 className="mt-2 font-display text-3xl text-[var(--color-ink)] sm:text-4xl">
                Conversación en vivo
              </h1>

              <div className="mt-6">
                <VoiceOrb
                  state={voiceState}
                  intensity={orbIntensity}
                  onClick={
                    useRealtimeVoice && voiceState === 'speaking'
                      ? () => void interrupt()
                      : undefined
                  }
                />
              </div>

              <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-[var(--color-muted)]">
                {statusHint}
              </p>

              {(error || voiceError) && (
                <div className="mt-6 text-left">
                  <ErrorState
                    message={voiceError?.message ?? error ?? 'Ocurrió un error.'}
                    onRetry={() => {
                      setError(null)
                      if (voiceError) {
                        void retry()
                      }
                    }}
                  />
                </div>
              )}

              {!isConnected && voiceState !== 'connecting' && (
                <div className="mt-8">
                  <Button
                    className="min-h-12 px-8"
                    onClick={() => {
                      setError(null)
                      void startSession(leadId)
                    }}
                  >
                    Iniciar conversación
                  </Button>
                  <p className="mt-3 text-xs text-[var(--color-muted)]">
                    El navegador pedirá permiso de micrófono.
                  </p>
                </div>
              )}

              {voiceState === 'connecting' && (
                <div className="mt-8 flex justify-center">
                  <Spinner label="Conectando voz" />
                </div>
              )}

              {isConnected && (
                <div className="mt-8 flex flex-wrap items-center justify-center gap-2">
                  <Button
                    variant="secondary"
                    className="gap-2"
                    onClick={toggleMute}
                    aria-label={isMuted ? 'Activar micrófono' : 'Silenciar micrófono'}
                  >
                    {isMuted ? <MicOff size={16} aria-hidden /> : <Mic size={16} aria-hidden />}
                    {isMuted ? 'Micrófono apagado' : 'Silenciar'}
                  </Button>
                  {voiceState === 'speaking' && (
                    <Button
                      variant="secondary"
                      className="gap-2"
                      onClick={() => void interrupt()}
                    >
                      <VolumeX size={16} aria-hidden /> Interrumpir
                    </Button>
                  )}
                  <Button variant="ghost" className="gap-2" onClick={() => void stopSession()}>
                    <PhoneOff size={16} aria-hidden /> Finalizar
                  </Button>
                </div>
              )}
            </motion.div>
          </section>

          <motion.div
            initial={{ opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.08 }}
            className="lg:sticky lg:top-6 lg:self-start"
          >
            <ProfileSidebar lead={leadQuery.data} />
          </motion.div>
        </div>
      </div>
    </AppShell>
  )
}
