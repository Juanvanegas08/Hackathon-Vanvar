import { Route, Routes } from 'react-router-dom'
import { AppProviders } from '@/providers/AppProviders'
import { AdvisorPage } from '@/pages/AdvisorPage'
import { ConsentPage } from '@/pages/ConsentPage'
import { ConversationPage } from '@/pages/ConversationPage'
import { DemoPage } from '@/pages/DemoPage'
import { HomePage } from '@/pages/HomePage'
import { IdentityPage } from '@/pages/IdentityPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { ResultsPage } from '@/pages/ResultsPage'

const App = () => (
  <AppProviders>
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/identification" element={<IdentityPage />} />
      <Route path="/consent" element={<ConsentPage />} />
      <Route path="/conversation/:leadId" element={<ConversationPage />} />
      <Route path="/results/:leadId" element={<ResultsPage />} />
      <Route path="/advisor" element={<AdvisorPage />} />
      <Route path="/demo" element={<DemoPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  </AppProviders>
)

export default App
