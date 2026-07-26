import {
  OpenAIRealtimeWebRTC,
  RealtimeSession,
} from '@openai/agents/realtime'
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PropsWithChildren,
} from 'react'
import { createRealtimeClientSecret } from '@/api/voice.api'
import { createCasaListaRealtimeAgent } from '@/features/voice/createCasaListaRealtimeAgent'
import { getVoiceContext } from '@/api/voice.api'
import { VoiceSessionContext } from '@/providers/voiceContext'
import type {
  VoiceMessage,
  VoiceSessionContextValue,
  VoiceSessionError,
  VoiceState,
} from '@/providers/voiceTypes'
import { getErrorMessage } from '@/utils/errors'

/** server_vad estricto (ruido) + menos eagerness (silence más largo). */
const BASE_TURN_DETECTION = {
  type: 'server_vad' as const,
  threshold: 0.72,
  prefixPaddingMs: 300,
  silenceDurationMs: 650,
  createResponse: true,
}

/** Tras el saludo: permite barge-in real del usuario. */
const ACTIVE_TURN_DETECTION = {
  ...BASE_TURN_DETECTION,
  interruptResponse: true,
}

/** Durante el intro: el ruido no debe cortar a Laura. */
const INTRO_TURN_DETECTION = {
  ...BASE_TURN_DETECTION,
  interruptResponse: false,
}

const INTRO_GUARD_MAX_MS = 10_000

const extractText = (item: unknown): string => {
  if (!item || typeof item !== 'object') return ''
  const record = item as Record<string, unknown>
  if (typeof record.transcript === 'string') return record.transcript
  if (typeof record.text === 'string') return record.text
  const content = record.content
  if (Array.isArray(content)) {
    return content
      .map((part) => {
        if (!part || typeof part !== 'object') return ''
        const chunk = part as Record<string, unknown>
        if (typeof chunk.transcript === 'string') return chunk.transcript
        if (typeof chunk.text === 'string') return chunk.text
        return ''
      })
      .filter(Boolean)
      .join(' ')
  }
  return ''
}

export const OpenAIRealtimeVoiceSessionProvider = ({ children }: PropsWithChildren) => {
  const [voiceState, setVoiceState] = useState<VoiceState>('idle')
  const [transcript, setTranscript] = useState('')
  const [userTranscript, setUserTranscript] = useState('')
  const [assistantTranscript, setAssistantTranscript] = useState('')
  const [conversationHistory, setConversationHistory] = useState<VoiceMessage[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [error, setError] = useState<VoiceSessionError | null>(null)

  const sessionRef = useRef<RealtimeSession | null>(null)
  const mediaStreamRef = useRef<MediaStream | null>(null)
  const audioElementRef = useRef<HTMLAudioElement | null>(null)
  const leadIdRef = useRef<string | null>(null)
  const clientSecretRef = useRef<string | null>(null)
  const completionPathRef = useRef<string | null>(null)
  const completionTimerRef = useRef<number | null>(null)
  const closingSpeechStartedRef = useRef(false)
  const onNavigateRef = useRef<((path: string) => void) | null>(null)
  const submitHandlerRef = useRef<((text: string) => Promise<void>) | null>(null)
  const introGuardActiveRef = useRef(false)
  const introSpeechSeenRef = useRef(false)
  const introGuardTimerRef = useRef<number | null>(null)
  const userMutedRef = useRef(false)

  const setMicEnabled = useCallback((enabled: boolean) => {
    mediaStreamRef.current?.getAudioTracks().forEach((track) => {
      track.enabled = enabled
    })
    try {
      sessionRef.current?.mute(!enabled)
    } catch {
      // ignore if transport already closed
    }
  }, [])

  const endIntroGuard = useCallback(() => {
    if (!introGuardActiveRef.current) return
    introGuardActiveRef.current = false
    introSpeechSeenRef.current = false
    if (introGuardTimerRef.current) {
      window.clearTimeout(introGuardTimerRef.current)
      introGuardTimerRef.current = null
    }
    // Reactiva barge-in tras el saludo.
    try {
      void sessionRef.current?.transport.updateSessionConfig({
        audio: {
          input: {
            noiseReduction: { type: 'near_field' },
            turnDetection: ACTIVE_TURN_DETECTION,
          },
        },
      })
    } catch {
      // ignore config race on teardown
    }
    if (!userMutedRef.current) {
      setMicEnabled(true)
    }
  }, [setMicEnabled])

  const cleanup = useCallback(async () => {
    if (completionTimerRef.current) {
      window.clearTimeout(completionTimerRef.current)
      completionTimerRef.current = null
    }
    if (introGuardTimerRef.current) {
      window.clearTimeout(introGuardTimerRef.current)
      introGuardTimerRef.current = null
    }
    introGuardActiveRef.current = false
    introSpeechSeenRef.current = false
    userMutedRef.current = false
    try {
      sessionRef.current?.close()
    } catch {
      // ignore close errors during teardown
    }
    sessionRef.current = null
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop())
    mediaStreamRef.current = null
    if (audioElementRef.current) {
      audioElementRef.current.pause()
      audioElementRef.current.srcObject = null
      audioElementRef.current = null
    }
    clientSecretRef.current = null
    completionPathRef.current = null
    closingSpeechStartedRef.current = false
    setIsConnected(false)
    setIsMuted(false)
  }, [])

  useEffect(() => {
    const onUnload = () => {
      mediaStreamRef.current?.getTracks().forEach((track) => track.stop())
      sessionRef.current?.close()
    }
    window.addEventListener('beforeunload', onUnload)
    return () => {
      window.removeEventListener('beforeunload', onUnload)
      void cleanup()
    }
  }, [cleanup])

  const scheduleNavigation = useCallback((path: string) => {
    completionPathRef.current = path
    closingSpeechStartedRef.current = false
    if (completionTimerRef.current) window.clearTimeout(completionTimerRef.current)
    // Fallback si por alguna razón no llega audio_stopped tras el cierre.
    completionTimerRef.current = window.setTimeout(() => {
      void cleanup().then(() => {
        setVoiceState('completed')
        onNavigateRef.current?.(path)
        completionPathRef.current = null
        closingSpeechStartedRef.current = false
      })
    }, 28_000)
  }, [cleanup])

  const startSession = useCallback(async (leadId?: string) => {
    if (!leadId) {
      setError({
        code: 'missing_lead',
        message: 'No encontramos la sesión del lead para iniciar la voz.',
      })
      setVoiceState('error')
      return
    }
    if (sessionRef.current) {
      await cleanup()
    }

    leadIdRef.current = leadId
    setError(null)
    setVoiceState('connecting')
    setConversationHistory([])
    setUserTranscript('')
    setAssistantTranscript('')

    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw Object.assign(new Error('Tu navegador no soporta WebRTC o micrófono.'), {
          code: 'webrtc_unsupported',
        })
      }

      const secretResponse = await createRealtimeClientSecret(leadId)
      clientSecretRef.current = secretResponse.client_secret

      const context = await getVoiceContext(leadId)
      const nextQ = context.next_question
      const initialContextSummary = [
        `display_name=${context.display_name ?? ''}`,
        `progress=${context.progress}`,
        `profile_completed=${context.profile_completed}`,
        nextQ
          ? `next_question.field=${nextQ.field}; next_question.intent=${nextQ.question}`
          : 'next_question=null',
        context.conversation_opening
          ? `opening_hint=${context.conversation_opening}`
          : '',
      ]
        .filter(Boolean)
        .join('\n')

      const mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })
      mediaStreamRef.current = mediaStream

      const audioElement = document.createElement('audio')
      audioElement.autoplay = true
      audioElementRef.current = audioElement

      const transport = new OpenAIRealtimeWebRTC({
        mediaStream,
        audioElement,
      })

      const agent = createCasaListaRealtimeAgent({
        leadId,
        displayName: context.display_name,
        voice: secretResponse.voice,
        initialContextSummary,
        onProfileCompleted: (path) => {
          scheduleNavigation(path)
        },
      })

      const session = new RealtimeSession(agent, {
        transport,
        model: secretResponse.model,
        config: {
          parallelToolCalls: false,
          audio: {
            input: {
              noiseReduction: { type: 'near_field' },
              turnDetection: INTRO_TURN_DETECTION,
            },
          },
        },
      })
      sessionRef.current = session

      session.on('audio_start', () => {
        setVoiceState('speaking')
        if (introGuardActiveRef.current) {
          introSpeechSeenRef.current = true
        }
        // Solo contamos el speech DE CIERRE (después de armar la navegación).
        if (completionPathRef.current) {
          closingSpeechStartedRef.current = true
        }
      })
      session.on('audio_stopped', () => {
        if (introGuardActiveRef.current && introSpeechSeenRef.current) {
          endIntroGuard()
        }
        if (completionPathRef.current && closingSpeechStartedRef.current) {
          if (completionTimerRef.current) {
            window.clearTimeout(completionTimerRef.current)
            completionTimerRef.current = null
          }
          const path = completionPathRef.current
          completionPathRef.current = null
          closingSpeechStartedRef.current = false
          void cleanup().then(() => {
            setVoiceState('completed')
            onNavigateRef.current?.(path)
          })
          return
        }
        setVoiceState(completionPathRef.current ? 'thinking' : 'listening')
      })
      session.on('audio_interrupted', () => {
        // Barge-in: corta estado de habla y deja listo para escuchar.
        if (introGuardActiveRef.current) {
          // Durante el intro no debería pasar; si pasa, rearmamos el guard.
          setVoiceState('speaking')
          return
        }
        setVoiceState('listening')
      })
      session.on('agent_tool_start', () => setVoiceState('thinking'))
      session.on('agent_tool_end', () => setVoiceState('thinking'))
      session.on('history_updated', (history) => {
        const messages: VoiceMessage[] = []
        let lastUser = ''
        let lastAssistant = ''
        history.forEach((item, index) => {
          const text = extractText(item)
          if (!text) return
          const roleRaw = (item as { role?: string }).role
          const role = roleRaw === 'user' ? 'user' : 'assistant'
          messages.push({
            id: `${role}-${index}`,
            role,
            text,
            at: Date.now(),
          })
          if (role === 'user') lastUser = text
          if (role === 'assistant') lastAssistant = text
        })
        setConversationHistory(messages)
        if (lastUser) {
          setUserTranscript(lastUser)
          setTranscript(lastUser)
        }
        if (lastAssistant) setAssistantTranscript(lastAssistant)
      })
      session.on('error', (event) => {
        setError({
          code: 'realtime_error',
          message: 'No pudimos iniciar la conversación de voz. Inténtalo de nuevo.',
        })
        setVoiceState('error')
        // Avoid logging secrets or full payloads.
        void event
      })

      await session.connect({
        apiKey: secretResponse.client_secret,
        model: secretResponse.model,
      })

      setIsConnected(true)
      setVoiceState('listening')

      // Protección de intro (B): mic mute + sin interrupt hasta que termine el saludo.
      introGuardActiveRef.current = true
      introSpeechSeenRef.current = false
      userMutedRef.current = false
      setMicEnabled(false)
      if (introGuardTimerRef.current) {
        window.clearTimeout(introGuardTimerRef.current)
      }
      introGuardTimerRef.current = window.setTimeout(() => {
        endIntroGuard()
      }, INTRO_GUARD_MAX_MS)

      // Kick off without a fake user bubble; context already in instructions.
      session.sendMessage(
        'Inicia ahora como Laura: saludo corto + marco humano ' +
          '("unas preguntas sencillas, tipo dos o tres minutos") + ' +
          'pregunta si lo hacen ahora o más tarde. ' +
          'Si opening_hint ya trae eso, reformúlalo natural. ' +
          'No suenes a formulario. Si ya tienes next_question/contexto, no llames tools primero.',
      )
    } catch (err) {
      await cleanup()
      const message = getErrorMessage(err)
      const code =
        typeof err === 'object' && err && 'code' in err
          ? String((err as { code?: string }).code ?? 'voice_start_failed')
          : message.toLowerCase().includes('permission') ||
              message.toLowerCase().includes('notallowed')
            ? 'microphone_denied'
            : 'voice_start_failed'
      setError({
        code,
        message:
          code === 'microphone_denied'
            ? 'Necesitamos permiso del micrófono para continuar por voz. Pulsa Iniciar conversación e acéptalo.'
            : 'No pudimos iniciar la conversación de voz. Inténtalo de nuevo.',
      })
      setVoiceState('error')
    }
  }, [cleanup, endIntroGuard, scheduleNavigation, setMicEnabled])

  const stopSession = useCallback(async () => {
    await cleanup()
    setVoiceState('idle')
    setTranscript('')
    setUserTranscript('')
    setAssistantTranscript('')
    setConversationHistory([])
    setError(null)
  }, [cleanup])

  const toggleMute = useCallback(() => {
    const next = !isMuted
    setIsMuted(next)
    userMutedRef.current = next
    // Durante el intro el mic ya está muteado; solo registra la preferencia del usuario.
    if (introGuardActiveRef.current) return
    setMicEnabled(!next)
  }, [isMuted, setMicEnabled])

  const interrupt = useCallback(async () => {
    const session = sessionRef.current
    if (!session) return
    if (introGuardActiveRef.current) {
      endIntroGuard()
    }
    try {
      session.interrupt()
    } catch {
      // ignore if transport already stopped
    }
    setVoiceState('listening')
  }, [endIntroGuard])

  const submitTextResponse = useCallback(async (text: string) => {
    setTranscript(text)
    setUserTranscript(text)
    if (sessionRef.current && isConnected) {
      setVoiceState('thinking')
      sessionRef.current.sendMessage(text)
      return
    }
    setVoiceState('thinking')
    try {
      await submitHandlerRef.current?.(text)
      setVoiceState('speaking')
      window.setTimeout(() => setVoiceState('listening'), 600)
    } catch (err) {
      setVoiceState('listening')
      throw err
    }
  }, [isConnected])

  const retry = useCallback(async () => {
    const leadId = leadIdRef.current
    await stopSession()
    if (leadId) await startSession(leadId)
  }, [startSession, stopSession])

  const setSubmitHandler = useCallback((fn: ((text: string) => Promise<void>) | null) => {
    submitHandlerRef.current = fn
  }, [])

  const value = useMemo<VoiceSessionContextValue>(
    () => ({
      voiceState,
      transcript,
      userTranscript,
      assistantTranscript,
      conversationHistory,
      isConnected,
      isMuted,
      error,
      providerName: 'openai',
      startSession,
      stopSession,
      toggleMute,
      interrupt,
      submitTextResponse,
      retry,
      setVoiceState,
      setTranscript,
      setSubmitHandler,
    }),
    [
      voiceState,
      transcript,
      userTranscript,
      assistantTranscript,
      conversationHistory,
      isConnected,
      isMuted,
      error,
      startSession,
      stopSession,
      toggleMute,
      interrupt,
      submitTextResponse,
      retry,
      setSubmitHandler,
    ],
  )

  // Expose navigation hook for ConversationPage via custom event.
  useEffect(() => {
    const handler = (event: Event) => {
      const custom = event as CustomEvent<(path: string) => void>
      onNavigateRef.current = custom.detail
    }
    window.addEventListener('casalista-voice-navigate', handler as EventListener)
    return () => window.removeEventListener('casalista-voice-navigate', handler as EventListener)
  }, [])

  return <VoiceSessionContext.Provider value={value}>{children}</VoiceSessionContext.Provider>
}
