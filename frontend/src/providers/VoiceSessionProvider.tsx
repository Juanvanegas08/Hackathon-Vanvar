import {
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type PropsWithChildren,
} from 'react'
import { VoiceSessionContext } from '@/providers/voiceContext'
import type {
  VoiceMessage,
  VoiceSessionContextValue,
  VoiceSessionError,
  VoiceState,
} from '@/providers/voiceTypes'

export type { VoiceState, VoiceMessage, VoiceSessionError, VoiceSessionContextValue }

/** Simulated voice session used when VITE_VOICE_PROVIDER=mock or as fallback. */
export const MockVoiceSessionProvider = ({ children }: PropsWithChildren) => {
  const [voiceState, setVoiceState] = useState<VoiceState>('idle')
  const [transcript, setTranscript] = useState('')
  const [userTranscript, setUserTranscript] = useState('')
  const [assistantTranscript, setAssistantTranscript] = useState('')
  const [conversationHistory, setConversationHistory] = useState<VoiceMessage[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [error, setError] = useState<VoiceSessionError | null>(null)
  const submitHandlerRef = useRef<((text: string) => Promise<void>) | null>(null)
  const leadIdRef = useRef<string | null>(null)

  const startSession = useCallback(async (leadId?: string) => {
    leadIdRef.current = leadId ?? null
    setError(null)
    setIsConnected(true)
    setVoiceState('listening')
  }, [])

  const stopSession = useCallback(async () => {
    setIsConnected(false)
    setVoiceState('idle')
    setTranscript('')
    setUserTranscript('')
    setAssistantTranscript('')
    setConversationHistory([])
    setIsMuted(false)
  }, [])

  const setSubmitHandler = useCallback((fn: ((text: string) => Promise<void>) | null) => {
    submitHandlerRef.current = fn
  }, [])

  const submitTextResponse = useCallback(async (text: string) => {
    setTranscript(text)
    setUserTranscript(text)
    setConversationHistory((prev) => [
      ...prev,
      { id: `user-${Date.now()}`, role: 'user', text, at: Date.now() },
    ])
    setVoiceState('thinking')
    try {
      await submitHandlerRef.current?.(text)
      setVoiceState('speaking')
      window.setTimeout(() => setVoiceState('listening'), 600)
    } catch (err) {
      setVoiceState('listening')
      throw err
    }
  }, [])

  const toggleMute = useCallback(() => {
    setIsMuted((value) => !value)
  }, [])

  const interrupt = useCallback(async () => {
    setVoiceState('listening')
  }, [])

  const retry = useCallback(async () => {
    setError(null)
    await startSession(leadIdRef.current ?? undefined)
  }, [startSession])

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
      providerName: 'mock',
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

  return <VoiceSessionContext.Provider value={value}>{children}</VoiceSessionContext.Provider>
}

export const useVoiceSession = () => {
  const context = useContext(VoiceSessionContext)
  if (!context) throw new Error('useVoiceSession must be used within VoiceSessionProvider')
  return context
}
