import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import type { ReactElement } from 'react'
import { FlowStoreProvider } from '@/store/flowStore'
import { VoiceSessionProvider } from '@/providers/SelectedVoiceSessionProvider'

export const renderWithProviders = (
  ui: ReactElement,
  {
    route = '/',
    path = '/',
  }: {
    route?: string
    path?: string
  } = {},
) => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[route]}>
        <FlowStoreProvider>
          <VoiceSessionProvider>
            <Routes>
              <Route path={path} element={ui} />
            </Routes>
          </VoiceSessionProvider>
        </FlowStoreProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
