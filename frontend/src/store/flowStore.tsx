import { createContext, useContext, useMemo, useState, type PropsWithChildren } from 'react'
import type { IdentityLookupResponse } from '@/api/types'
import { clearSessionLeadId, getSessionLeadId, setSessionLeadId } from '@/utils/session'

interface FlowStoreValue {
  documentType: string
  documentNumber: string
  lookupResult: IdentityLookupResponse | null
  leadId: string | null
  consentGranted: boolean
  setDocument: (type: string, number: string) => void
  setLookup: (result: IdentityLookupResponse | null) => void
  setLeadId: (id: string | null) => void
  setConsentGranted: (granted: boolean) => void
  reset: () => void
}

const FlowStoreContext = createContext<FlowStoreValue | null>(null)

export const FlowStoreProvider = ({ children }: PropsWithChildren) => {
  const [documentType, setDocumentType] = useState('CC')
  const [documentNumber, setDocumentNumber] = useState('')
  const [lookupResult, setLookup] = useState<IdentityLookupResponse | null>(null)
  const [leadId, setLeadIdState] = useState<string | null>(getSessionLeadId)
  const [consentGranted, setConsentGranted] = useState(false)
  const value = useMemo<FlowStoreValue>(() => ({
    documentType, documentNumber, lookupResult, leadId, consentGranted,
    setDocument: (type, number) => { setDocumentType(type); setDocumentNumber(number) },
    setLookup,
    setLeadId: (id) => { setLeadIdState(id); if (id) setSessionLeadId(id); else clearSessionLeadId() },
    setConsentGranted,
    reset: () => { setDocumentType('CC'); setDocumentNumber(''); setLookup(null); setLeadIdState(null); setConsentGranted(false); clearSessionLeadId() },
  }), [documentType, documentNumber, lookupResult, leadId, consentGranted])
  return <FlowStoreContext.Provider value={value}>{children}</FlowStoreContext.Provider>
}

export const useFlowStore = () => {
  const context = useContext(FlowStoreContext)
  if (!context) throw new Error('useFlowStore must be used within FlowStoreProvider')
  return context
}
