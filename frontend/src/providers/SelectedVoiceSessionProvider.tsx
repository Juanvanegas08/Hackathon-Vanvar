import type { PropsWithChildren } from 'react'
import { MockVoiceSessionProvider } from '@/providers/VoiceSessionProvider'
import { OpenAIRealtimeVoiceSessionProvider } from '@/providers/OpenAIRealtimeVoiceSessionProvider'

const provider = (import.meta.env.VITE_VOICE_PROVIDER || 'mock').toLowerCase()
const voiceEnabled = import.meta.env.VITE_VOICE_ENABLED !== 'false'

export const VoiceSessionProvider = ({ children }: PropsWithChildren) => {
  if (voiceEnabled && provider === 'openai') {
    return <OpenAIRealtimeVoiceSessionProvider>{children}</OpenAIRealtimeVoiceSessionProvider>
  }
  return <MockVoiceSessionProvider>{children}</MockVoiceSessionProvider>
}
