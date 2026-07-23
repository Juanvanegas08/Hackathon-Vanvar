export type VoiceState =
  | 'idle'
  | 'connecting'
  | 'listening'
  | 'thinking'
  | 'speaking'
  | 'confirming'
  | 'completed'
  | 'error'

export type VoiceMessageRole = 'user' | 'assistant' | 'system'

export interface VoiceMessage {
  id: string
  role: VoiceMessageRole
  text: string
  at: number
}

export interface VoiceSessionError {
  code: string
  message: string
}

export interface VoiceSessionContextValue {
  voiceState: VoiceState
  transcript: string
  userTranscript: string
  assistantTranscript: string
  conversationHistory: VoiceMessage[]
  isConnected: boolean
  isMuted: boolean
  error: VoiceSessionError | null
  providerName: 'mock' | 'openai'
  startSession: (leadId?: string) => Promise<void>
  stopSession: () => Promise<void>
  toggleMute: () => void
  interrupt: () => Promise<void>
  submitTextResponse: (text: string) => Promise<void>
  retry: () => Promise<void>
  setVoiceState: (state: VoiceState) => void
  setTranscript: (transcript: string) => void
  setSubmitHandler: (fn: ((text: string) => Promise<void>) | null) => void
}
