import { useMutation } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { createLeadFromIdentity } from '@/api/identity.api'
import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/Button'
import { ErrorState } from '@/components/ui/ErrorState'
import { Spinner } from '@/components/ui/Spinner'
import { useFlowStore } from '@/store/flowStore'
import { getErrorMessage } from '@/utils/errors'

export const ConsentPage = () => {
  const navigate = useNavigate()
  const { documentType, documentNumber, lookupResult, setLeadId, setConsentGranted } =
    useFlowStore()
  const [error, setError] = useState<string | null>(null)
  const autoStarted = useRef(false)

  const createMutation = useMutation({
    mutationFn: (dataConsent: boolean) =>
      createLeadFromIdentity(documentType, documentNumber, dataConsent),
    onSuccess: (result, dataConsent) => {
      setConsentGranted(dataConsent)
      setLeadId(result.lead.id)
      navigate(`/conversation/${result.lead.id}`, { replace: true })
    },
    onError: (err) => setError(getErrorMessage(err)),
  })

  const createLead = createMutation.mutate

  const profile = lookupResult?.prefilled_profile ?? {}
  const category =
    typeof profile.categoria_afiliacion === 'string' ? profile.categoria_afiliacion : null
  const company = typeof profile.empresa === 'string' ? profile.empresa : null
  const affiliated = profile.afiliado === true
  const hasUsefulPrefill = Boolean(
    lookupResult &&
      (lookupResult.prefilled_fields.length > 0 ||
        affiliated ||
        Boolean(category) ||
        Boolean(company)),
  )

  // Sin datos útiles: saltar resumen/autorización y abrir conversación.
  useEffect(() => {
    if (!lookupResult || !documentNumber) return
    if (hasUsefulPrefill) return
    if (autoStarted.current) return
    autoStarted.current = true
    createLead(true)
  }, [lookupResult, documentNumber, hasUsefulPrefill, createLead])

  const [showKnownIntro, setShowKnownIntro] = useState(hasUsefulPrefill)

  useEffect(() => {
    if (!hasUsefulPrefill) return
    const timer = window.setTimeout(() => setShowKnownIntro(false), 2200)
    return () => window.clearTimeout(timer)
  }, [hasUsefulPrefill])

  if (!lookupResult || !documentNumber) {
    return <Navigate to="/identification" replace />
  }

  if (!hasUsefulPrefill) {
    return (
      <AppShell>
        <div className="mx-auto flex min-h-[60vh] max-w-lg flex-col items-center justify-center gap-6 text-center">
          {error ? (
            <ErrorState
              message={error}
              onRetry={() => {
                autoStarted.current = false
                setError(null)
                createMutation.mutate(true)
              }}
            />
          ) : (
            <>
              <Spinner label="Preparando tu conversación con Laura" />
              <p className="max-w-sm text-sm text-[var(--color-muted)]">
                No encontramos información útil para precargar. Te llevamos con Laura para armar
                tu perfil por voz.
              </p>
            </>
          )}
        </div>
      </AppShell>
    )
  }

  if (showKnownIntro) {
    return (
      <AppShell>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mx-auto flex min-h-[60vh] max-w-2xl flex-col justify-center text-left"
        >
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--color-green)]">
            Buenas noticias
          </p>
          <h1 className="mt-3 font-display text-4xl sm:text-5xl">
            Ya conocemos una parte de tu perfil.
          </h1>
          <p className="mt-4 text-lg text-[var(--color-muted)]">
            Encontramos información básica sobre tu afiliación y algunas características de tu
            perfil. Podemos utilizarla para que la conversación sea más corta.
          </p>
        </motion.div>
      </AppShell>
    )
  }

  return (
    <AppShell>
      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mx-auto max-w-2xl py-10 text-left"
      >
        <div className="mb-8 rounded-[2rem] bg-white p-6 surface-shadow">
          <h2 className="font-display text-2xl">Resumen no invasivo</h2>
          <ul className="mt-4 space-y-2 text-[var(--color-muted)]">
            <li>
              Afiliación:{' '}
              <strong className="text-[var(--color-ink)]">
                {affiliated ? 'Afiliado(a)' : 'No afiliado(a)'}
              </strong>
            </li>
            {category && (
              <li>
                Categoría: <strong className="text-[var(--color-ink)]">{category}</strong>
              </li>
            )}
            {company && (
              <li>
                Empresa: <strong className="text-[var(--color-ink)]">{company}</strong>
              </li>
            )}
            <li>
              Datos que pueden precargarse:{' '}
              <strong className="text-[var(--color-ink)]">
                {lookupResult.prefilled_fields.length}
              </strong>
            </li>
          </ul>
          <p className="mt-4 text-sm text-[var(--color-muted)]">
            No mostramos salarios ni datos sensibles en este paso. La identidad permanece sin
            verificar (sin OTP).
          </p>
        </div>

        <h1 className="font-display text-3xl leading-tight sm:text-4xl">
          ¿Nos autorizas a usar esta información para personalizar tu orientación de vivienda?
        </h1>
        <p className="mt-4 text-[var(--color-muted)]">
          <strong className="text-[var(--color-ink)]">Continuar</strong> usa tu perfil
          encontrado.{' '}
          <strong className="text-[var(--color-ink)]">Empezar desde cero</strong> ignora esos
          datos y arma el perfil solo con la conversación.
        </p>

        {error && (
          <div className="mt-6">
            <ErrorState message={error} onRetry={() => setError(null)} />
          </div>
        )}

        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <Button
            className="min-h-14 flex-1 text-lg"
            disabled={createMutation.isPending}
            onClick={() => createMutation.mutate(true)}
          >
            Continuar con mi perfil
          </Button>
          <Button
            variant="secondary"
            className="min-h-14 flex-1 text-lg"
            disabled={createMutation.isPending}
            onClick={() => createMutation.mutate(false)}
          >
            Empezar desde cero
          </Button>
        </div>

        <Link
          to="/identification"
          className="mt-8 inline-block text-sm text-[var(--color-blue)] hover:underline"
        >
          Cambiar documento
        </Link>
      </motion.section>
    </AppShell>
  )
}
