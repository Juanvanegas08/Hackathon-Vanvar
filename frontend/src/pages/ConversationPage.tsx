import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { Mic, MicOff, PhoneOff, VolumeX } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { confirmPrefilledData } from '@/api/identity.api'
import {
  evaluateLead,
  getLead,
  getNextQuestion,
  getSummary,
  updateLead,
} from '@/api/leads.api'
import { getRecommendations } from '@/api/recommendations.api'
import type { NextQuestion } from '@/api/types'
import { ProfileSidebar } from '@/components/conversation/ProfileSidebar'
import { QuestionPanel } from '@/components/conversation/QuestionPanel'
import { VoiceOrb } from '@/components/conversation/VoiceOrb'
import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/Button'
import { ErrorState } from '@/components/ui/ErrorState'
import { Spinner } from '@/components/ui/Spinner'
import { useVoiceSession } from '@/providers/VoiceSessionProvider'
import { adaptAnswer, isConfirmationPayload } from '@/utils/answerAdapter'
import { getErrorMessage } from '@/utils/errors'
import { setSessionLeadId } from '@/utils/session'

export const ConversationPage = () => {
  const { leadId = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const {
    voiceState,
    startSession,
    stopSession,
    setVoiceState,
    setSubmitHandler,
    submitTextResponse,
    providerName,
    isConnected,
    isMuted,
    toggleMute,
    interrupt,
    error: voiceError,
    retry,
    userTranscript,
    assistantTranscript,
    conversationHistory,
  } = useVoiceSession()

  const [question, setQuestion] = useState<NextQuestion | null>(null)
  const [completed, setCompleted] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [finishing, setFinishing] = useState(false)
  const [showTextInput, setShowTextInput] = useState(true)
  const [forceTextMode, setForceTextMode] = useState(providerName === 'mock')
  const [historyOpen, setHistoryOpen] = useState(false)
  const [voiceStarted, setVoiceStarted] = useState(false)

  const useRealtimeVoice = providerName === 'openai' && !forceTextMode

  useEffect(() => {
    if (leadId) setSessionLeadId(leadId)
  }, [leadId])

  useEffect(() => {
    const handler = (path: string) => {
      void stopSession().finally(() => navigate(path))
    }
    window.dispatchEvent(new CustomEvent('casalista-voice-navigate', { detail: handler }))
  }, [navigate, stopSession])

  const leadQuery = useQuery({
    queryKey: ['lead', leadId],
    queryFn: () => getLead(leadId),
    enabled: Boolean(leadId),
    retry: false,
  })

  const loadQuestion = useCallback(async () => {
    if (!leadId || useRealtimeVoice) return
    setError(null)
    setVoiceState('thinking')
    try {
      const next = await getNextQuestion(leadId)
      if (next.completed || !next.next_question) {
        setCompleted(true)
        setQuestion(null)
        setVoiceState('completed')
        return
      }
      setQuestion(next.next_question)
      setVoiceState(
        next.next_question.type === 'confirmation' ? 'confirming' : 'speaking',
      )
      window.setTimeout(() => setVoiceState('listening'), 700)
    } catch (err) {
      setError(getErrorMessage(err))
      setVoiceState('idle')
    }
  }, [leadId, setVoiceState, useRealtimeVoice])

  useEffect(() => {
    if (!useRealtimeVoice) {
      void startSession(leadId)
      void loadQuestion()
    }
  }, [leadId, loadQuestion, startSession, useRealtimeVoice])

  const finishProfile = useCallback(async () => {
    if (!leadId || useRealtimeVoice) return
    setFinishing(true)
    setError(null)
    setVoiceState('thinking')
    try {
      await evaluateLead(leadId)
      await Promise.all([
        getRecommendations(leadId, { limit: 3 }),
        getSummary(leadId),
      ])
      navigate(`/results/${leadId}`)
    } catch (err) {
      setError(getErrorMessage(err))
      setFinishing(false)
      setVoiceState('idle')
    }
  }, [leadId, navigate, setVoiceState, useRealtimeVoice])

  useEffect(() => {
    if (!useRealtimeVoice && completed && !finishing) void finishProfile()
  }, [completed, finishing, finishProfile, useRealtimeVoice])

  const answerMutation = useMutation({
    mutationFn: async (answer: string | boolean | number) => {
      if (!leadId || !question) return
      setVoiceState('thinking')
      const payload = adaptAnswer(question, answer)
      if (isConfirmationPayload(payload)) {
        await confirmPrefilledData(leadId, payload)
      } else {
        await updateLead(leadId, payload)
      }
      await queryClient.invalidateQueries({ queryKey: ['lead', leadId] })
      const next = await getNextQuestion(leadId)
      if (next.completed || !next.next_question) {
        setCompleted(true)
        setQuestion(null)
        setVoiceState('completed')
        return
      }
      setQuestion(next.next_question)
      setVoiceState(
        next.next_question.type === 'confirmation' ? 'confirming' : 'speaking',
      )
      window.setTimeout(() => setVoiceState('listening'), 500)
    },
    onError: (err) => {
      setError(getErrorMessage(err))
      setVoiceState('listening')
    },
  })

  useEffect(() => {
    setSubmitHandler(async (text) => {
      if (useRealtimeVoice && isConnected) {
        await submitTextResponse(text)
        return
      }
      await answerMutation.mutateAsync(text)
    })
    return () => setSubmitHandler(null)
  }, [answerMutation, isConnected, setSubmitHandler, submitTextResponse, useRealtimeVoice])

  useEffect(() => {
    if (!useRealtimeVoice || !isConnected) return
    const timer = window.setInterval(() => {
      void queryClient.invalidateQueries({ queryKey: ['lead', leadId] })
    }, 4000)
    return () => window.clearInterval(timer)
  }, [isConnected, leadId, queryClient, useRealtimeVoice])

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
    return (
      <AppShell>
        <div className="mx-auto max-w-lg py-16">
          <ErrorState
            message="La sesión de demostración ya no está disponible. Podemos comenzar una nueva."
            onRetry={() => navigate('/identification')}
          />
          <Link to="/" className="mt-4 inline-block text-[var(--color-blue)] hover:underline">
            Ir al inicio
          </Link>
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell>
      <div className="grid gap-8 py-6 lg:grid-cols-[1.35fr_0.65fr]">
        <section className="text-center lg:text-left">
          <div className="mb-8 flex flex-col items-center gap-4 lg:items-start">
            <VoiceOrb
              state={finishing ? 'thinking' : voiceState}
              onClick={
                useRealtimeVoice && voiceState === 'speaking'
                  ? () => void interrupt()
                  : undefined
              }
            />
            <p className="max-w-md text-sm text-[var(--color-muted)]">
              {finishing
                ? 'Estamos preparando tus mejores opciones.'
                : useRealtimeVoice
                  ? 'Estás conversando con un asistente de voz generado por inteligencia artificial.'
                  : 'Una pregunta a la vez. Puedes responder con botones o texto.'}
            </p>
          </div>

          {(error || voiceError) && (
            <div className="mb-6">
              <ErrorState
                message={voiceError?.message ?? error ?? 'Ocurrió un error.'}
                onRetry={() => {
                  if (voiceError) {
                    void retry()
                    return
                  }
                  void loadQuestion()
                }}
              />
              {useRealtimeVoice && (
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setForceTextMode(true)
                      void stopSession()
                      void startSession(leadId)
                      void loadQuestion()
                    }}
                  >
                    Continuar por texto
                  </Button>
                  <Button variant="ghost" onClick={() => navigate('/')}>
                    Volver al inicio
                  </Button>
                </div>
              )}
            </div>
          )}

          {useRealtimeVoice && !voiceStarted && !isConnected && voiceState !== 'connecting' && (
            <div className="mb-8 rounded-[2rem] bg-white p-6 text-left surface-shadow">
              <h2 className="font-display text-2xl">¿Listo para hablar?</h2>
              <p className="mt-2 text-[var(--color-muted)]">
                Al continuar, el navegador pedirá permiso para usar tu micrófono.
              </p>
              <div className="mt-5 flex flex-wrap gap-3">
                <Button
                  className="min-h-12"
                  onClick={() => {
                    setVoiceStarted(true)
                    void startSession(leadId)
                  }}
                >
                  Iniciar conversación
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => {
                    setForceTextMode(true)
                    void startSession(leadId)
                    void loadQuestion()
                  }}
                >
                  Prefiero continuar por texto
                </Button>
              </div>
            </div>
          )}

          {useRealtimeVoice && (userTranscript || assistantTranscript) && (
            <div className="mb-6 rounded-3xl border border-[var(--color-line)] bg-white/90 p-4 text-left text-sm">
              {assistantTranscript && (
                <p>
                  <span className="font-semibold text-[var(--color-blue)]">CasaLista:</span>{' '}
                  {assistantTranscript}
                </p>
              )}
              {userTranscript && (
                <p className="mt-2">
                  <span className="font-semibold text-[var(--color-green)]">Tú:</span>{' '}
                  {userTranscript}
                </p>
              )}
              <button
                type="button"
                className="mt-3 text-xs font-semibold text-[var(--color-blue)]"
                onClick={() => setHistoryOpen((value) => !value)}
              >
                {historyOpen ? 'Ocultar historial' : 'Ver historial'}
              </button>
              {historyOpen && (
                <ul className="mt-3 max-h-40 space-y-2 overflow-y-auto text-[var(--color-muted)]">
                  {conversationHistory.map((item) => (
                    <li key={item.id}>
                      <strong>{item.role === 'user' ? 'Tú' : 'CasaLista'}:</strong> {item.text}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          <AnimatePresence mode="wait">
            {!useRealtimeVoice && question && !finishing && showTextInput && (
              <motion.div
                key={question.field + question.question}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.28 }}
              >
                <QuestionPanel
                  question={question}
                  disabled={answerMutation.isPending}
                  onAnswer={(answer) => answerMutation.mutate(answer)}
                />
              </motion.div>
            )}
          </AnimatePresence>

          {useRealtimeVoice && showTextInput && isConnected && (
            <form
              className="mt-4 flex flex-col gap-3 sm:flex-row"
              onSubmit={(event) => {
                event.preventDefault()
                const form = event.currentTarget
                const input = form.elements.namedItem('voice-text') as HTMLInputElement
                const value = input.value.trim()
                if (!value) return
                void submitTextResponse(value)
                input.value = ''
              }}
            >
              <input
                name="voice-text"
                aria-label="Escribir respuesta"
                className="w-full rounded-2xl border border-[var(--color-line)] bg-white px-4 py-3"
                placeholder="También puedes escribir tu respuesta"
              />
              <Button type="submit" className="min-h-12">
                Enviar
              </Button>
            </form>
          )}

          {(finishing || answerMutation.isPending || voiceState === 'connecting') && (
            <div className="mt-8 flex justify-center lg:justify-start">
              <Spinner
                label={
                  voiceState === 'connecting'
                    ? 'Conectando voz'
                    : finishing
                      ? 'Preparando resultados'
                      : 'Procesando respuesta'
                }
              />
            </div>
          )}

          <div className="mt-8 flex flex-wrap items-center justify-center gap-3 lg:justify-start">
            {useRealtimeVoice && isConnected && (
              <>
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
                <Button
                  variant="ghost"
                  className="gap-2"
                  onClick={() => void stopSession()}
                >
                  <PhoneOff size={16} aria-hidden /> Finalizar voz
                </Button>
              </>
            )}
            <Button variant="ghost" onClick={() => setShowTextInput((value) => !value)}>
              {showTextInput ? 'Ocultar escritura' : 'Escribir respuesta'}
            </Button>
          </div>
        </section>

        <div className="lg:sticky lg:top-6 lg:self-start">
          <ProfileSidebar lead={leadQuery.data} />
        </div>
      </div>
    </AppShell>
  )
}
