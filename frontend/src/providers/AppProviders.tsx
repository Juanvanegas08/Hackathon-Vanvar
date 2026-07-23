import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import type { PropsWithChildren } from 'react'
import { VoiceSessionProvider } from '@/providers/SelectedVoiceSessionProvider'
import { FlowStoreProvider } from '@/store/flowStore'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
})

export const AppProviders = ({ children }: PropsWithChildren) => (
  <QueryClientProvider client={queryClient}>
    <BrowserRouter>
      <FlowStoreProvider>
        <VoiceSessionProvider>{children}</VoiceSessionProvider>
      </FlowStoreProvider>
    </BrowserRouter>
  </QueryClientProvider>
)
