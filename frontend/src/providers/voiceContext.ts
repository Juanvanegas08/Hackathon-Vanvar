import { createContext } from 'react'
import type { VoiceSessionContextValue } from '@/providers/voiceTypes'

export const VoiceSessionContext = createContext<VoiceSessionContextValue | null>(null)
