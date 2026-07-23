import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { listDemoIdentities, lookupIdentity } from '@/api/identity.api'
import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/Button'
import { ErrorState } from '@/components/ui/ErrorState'
import { Spinner } from '@/components/ui/Spinner'
import { TextField } from '@/components/ui/TextField'
import { useFlowStore } from '@/store/flowStore'
import { getErrorMessage } from '@/utils/errors'

const demoMode = import.meta.env.VITE_DEMO_MODE === 'true'

export const IdentityPage = () => {
  const navigate = useNavigate()
  const { documentType, documentNumber, setDocument, setLookup } = useFlowStore()
  const [localType, setLocalType] = useState(documentType || 'CC')
  const [localNumber, setLocalNumber] = useState(documentNumber)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (documentType) setLocalType(documentType)
    if (documentNumber) setLocalNumber(documentNumber)
  }, [documentType, documentNumber])

  const demoQuery = useQuery({
    queryKey: ['demo-identities'],
    queryFn: listDemoIdentities,
    enabled: demoMode,
    retry: false,
  })

  const lookupMutation = useMutation({
    mutationFn: () => lookupIdentity(localType, localNumber.trim()),
    onSuccess: (result) => {
      setDocument(localType, localNumber.trim())
      setLookup(result)
      navigate('/consent')
    },
    onError: (err) => setError(getErrorMessage(err)),
  })

  return (
    <AppShell>
      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mx-auto max-w-2xl py-10 text-left"
      >
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--color-green)]">
          Empezamos
        </p>
        <h1 className="mt-3 font-display text-4xl leading-tight text-[var(--color-ink)] sm:text-5xl">
          Antes de comenzar, podemos revisar si ya contamos con información básica sobre tu
          afiliación.
        </h1>
        <p className="mt-4 text-lg text-[var(--color-muted)]">
          Solo necesitamos tu documento. Nada más por ahora.
        </p>

        <form
          className="mt-10 space-y-5 rounded-[2rem] bg-white p-6 surface-shadow sm:p-8"
          onSubmit={(event) => {
            event.preventDefault()
            setError(null)
            lookupMutation.mutate()
          }}
        >
          <div className="grid gap-4 sm:grid-cols-[140px_1fr]">
            <label className="block space-y-1.5 text-sm font-medium">
              Tipo
              <select
                className="w-full rounded-2xl border border-[var(--color-line)] bg-white px-4 py-3"
                value={localType}
                onChange={(event) => setLocalType(event.target.value)}
                aria-label="Tipo de documento"
              >
                <option value="CC">CC</option>
                <option value="CE">CE</option>
                <option value="PA">PA</option>
              </select>
            </label>
            <TextField
              id="document-number"
              label="Número de documento"
              value={localNumber}
              onChange={(event) => setLocalNumber(event.target.value)}
              inputMode="numeric"
              autoComplete="off"
              required
            />
          </div>
          {error && <ErrorState message={error} onRetry={() => lookupMutation.mutate()} />}
          <Button type="submit" className="min-h-14 w-full text-lg" disabled={lookupMutation.isPending || !localNumber.trim()}>
            {lookupMutation.isPending ? 'Consultando…' : 'Continuar'}
          </Button>
        </form>

        {demoMode && (
          <div className="mt-10">
            <h2 className="font-display text-xl">Escenarios para la demostración</h2>
            <p className="mt-1 text-sm text-[var(--color-muted)]">
              Perfiles completamente ficticios para el jurado.
            </p>
            {demoQuery.isLoading && <div className="mt-4"><Spinner label="Cargando escenarios" /></div>}
            {demoQuery.isError && (
              <p className="mt-4 text-sm text-[var(--color-muted)]">
                No pudimos cargar escenarios demo. Puedes escribir un documento manualmente.
              </p>
            )}
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {(demoQuery.data ?? []).map((item) => (
                <button
                  key={item.document_number}
                  type="button"
                  className="rounded-2xl border border-[var(--color-line)] bg-white p-4 text-left transition hover:border-[var(--color-yellow)]"
                  onClick={() => {
                    setLocalType(item.document_type)
                    setLocalNumber(item.document_number)
                  }}
                >
                  <p className="font-semibold text-[var(--color-ink)]">{item.name}</p>
                  <p className="mt-1 text-sm text-[var(--color-muted)]">
                    {item.document_type} {item.document_number}
                  </p>
                  <p className="mt-2 text-sm text-[var(--color-blue)]">{item.scenario}</p>
                </button>
              ))}
            </div>
          </div>
        )}

        <Link to="/" className="mt-8 inline-block text-sm text-[var(--color-blue)] hover:underline">
          Volver al inicio
        </Link>
      </motion.section>
    </AppShell>
  )
}
