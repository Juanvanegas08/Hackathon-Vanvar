import { useMutation } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { MessageCircle, Phone } from 'lucide-react'
import { requestPhoneCall } from '@/api/phone.api'
import { BrochureShowcase } from '@/components/home/BrochureShowcase'
import { AmbientBackground } from '@/components/layout/AmbientBackground'
import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { TextField } from '@/components/ui/TextField'
import { getErrorMessage } from '@/utils/errors'

type CallMode = 'now' | 'schedule'

const toLocalInputValue = (date: Date) => {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export const HomePage = () => {
  const navigate = useNavigate()
  const [callModalOpen, setCallModalOpen] = useState(false)
  const [mode, setMode] = useState<CallMode>('now')
  const [phone, setPhone] = useState('')
  const [documentType, setDocumentType] = useState<'CC' | 'CE' | 'PP' | 'NIT'>('CC')
  const [documentNumber, setDocumentNumber] = useState('')
  const [scheduledLocal, setScheduledLocal] = useState(() => {
    const d = new Date(Date.now() + 15 * 60_000)
    return toLocalInputValue(d)
  })
  const [consent, setConsent] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const minSchedule = useMemo(() => toLocalInputValue(new Date(Date.now() + 2 * 60_000)), [])

  const callMutation = useMutation({
    mutationFn: requestPhoneCall,
    onSuccess: (result) => {
      setFormError(null)
      setSuccessMessage(result.message)
    },
    onError: (err) => {
      setSuccessMessage(null)
      setFormError(getErrorMessage(err))
    },
  })

  const resetModal = () => {
    setCallModalOpen(false)
    setFormError(null)
    setSuccessMessage(null)
    callMutation.reset()
  }

  const submitCall = () => {
    setFormError(null)
    setSuccessMessage(null)
    if (!phone.trim() || !documentNumber.trim()) {
      setFormError('Completa teléfono y documento.')
      return
    }
    if (!consent) {
      setFormError('Debes aceptar el consentimiento de datos.')
      return
    }
    const scheduledAt =
      mode === 'schedule' ? new Date(scheduledLocal).toISOString() : undefined
    if (mode === 'schedule' && Number.isNaN(Date.parse(scheduledLocal))) {
      setFormError('La fecha programada no es válida.')
      return
    }
    callMutation.mutate({
      phone: phone.trim(),
      mode,
      scheduled_at: scheduledAt,
      document_type: documentType,
      document_number: documentNumber.trim(),
      data_consent: true,
    })
  }

  return (
    <AppShell>
      <section className="relative isolate overflow-visible pb-6 pt-2 sm:pb-8">
        <div
          className="hero-bubbles pointer-events-none absolute left-1/2 w-screen -translate-x-1/2"
          style={{ top: '-5.5rem', bottom: '-1rem' }}
        >
          <AmbientBackground />
        </div>

        <div className="relative z-10 max-w-2xl text-left lg:max-w-3xl">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55 }}
          >
            <h1 className="font-display text-4xl leading-[1.05] tracking-tight text-[var(--color-ink)] sm:text-5xl lg:text-6xl">
              CasaLista
            </h1>
            <p className="mt-3 max-w-xl text-xl font-medium leading-snug text-[var(--color-ink)] sm:mt-4 sm:text-2xl">
              Tu camino a vivienda puede comenzar con una conversación.
            </p>
            <p className="mt-3 max-w-lg text-base text-[var(--color-muted)] sm:mt-4 sm:text-lg">
              Cuéntanos qué buscas y te orientamos con proyectos alineados a tu perfil, listos para
              avanzar con un asesor.
            </p>
            <div className="mt-6 flex flex-wrap items-center gap-3 sm:mt-7">
              <Button
                className="min-h-12 gap-2 px-7 text-base sm:min-h-14 sm:px-8 sm:text-lg"
                onClick={() => navigate('/identification')}
              >
                Hablar ahora
              </Button>
              <Button
                variant="secondary"
                className="min-h-12 gap-2 px-6 text-base sm:min-h-14 sm:px-7 sm:text-lg"
                onClick={() => {
                  setSuccessMessage(null)
                  setFormError(null)
                  setCallModalOpen(true)
                }}
              >
                <Phone size={18} aria-hidden /> Prefiero que me llamen
              </Button>
            </div>
            <button
              type="button"
              className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-[var(--color-blue)] underline-offset-4 hover:underline"
              onClick={() => navigate('/identification')}
            >
              <MessageCircle size={16} aria-hidden /> Prefiero continuar por texto
            </button>
          </motion.div>
        </div>
      </section>

      <BrochureShowcase />

      <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--color-line)] py-8 text-sm text-[var(--color-muted)]">
        <span>CasaLista · Colsubsidio</span>
        <Link to="/demo" className="font-medium text-[var(--color-blue)] hover:underline">
          Probar escenarios
        </Link>
      </footer>

      <Modal open={callModalOpen} title="Que Laura te llame" onClose={resetModal}>
        {successMessage ? (
          <div className="space-y-4">
            <p className="text-[var(--color-ink)]">{successMessage}</p>
            <p className="text-sm text-[var(--color-muted)]">
              Contesta desde el número que registraste. Si tu cuenta Twilio sigue en trial, el
              destino debe estar verificado.
            </p>
            <Button onClick={resetModal}>Listo</Button>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-[var(--color-muted)]">
              Misma asesora Laura y el mismo perfil que en la web. Elige si te llamamos ahora o en
              otro momento.
            </p>

            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant={mode === 'now' ? 'primary' : 'secondary'}
                onClick={() => setMode('now')}
              >
                Ahora
              </Button>
              <Button
                type="button"
                variant={mode === 'schedule' ? 'primary' : 'secondary'}
                onClick={() => setMode('schedule')}
              >
                Programar
              </Button>
            </div>

            <TextField
              label="Celular"
              name="phone"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="3001234567 o +573001234567"
              autoComplete="tel"
            />

            <div className="grid gap-3 sm:grid-cols-[7rem_1fr]">
              <label className="block text-sm font-medium text-[var(--color-ink)]">
                Documento
                <select
                  className="mt-1 w-full rounded-xl border border-[var(--color-line)] bg-white px-3 py-2"
                  value={documentType}
                  onChange={(e) =>
                    setDocumentType(e.target.value as 'CC' | 'CE' | 'PP' | 'NIT')
                  }
                >
                  <option value="CC">CC</option>
                  <option value="CE">CE</option>
                  <option value="PP">PP</option>
                  <option value="NIT">NIT</option>
                </select>
              </label>
              <TextField
                label="Número"
                name="document_number"
                value={documentNumber}
                onChange={(e) => setDocumentNumber(e.target.value)}
                placeholder="Número de documento"
              />
            </div>

            {mode === 'schedule' && (
              <label className="block text-sm font-medium text-[var(--color-ink)]">
                Fecha y hora
                <input
                  type="datetime-local"
                  className="mt-1 w-full rounded-xl border border-[var(--color-line)] bg-white px-3 py-2"
                  min={minSchedule}
                  value={scheduledLocal}
                  onChange={(e) => setScheduledLocal(e.target.value)}
                />
              </label>
            )}

            <label className="flex items-start gap-3 text-sm text-[var(--color-muted)]">
              <input
                type="checkbox"
                className="mt-1"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
              />
              <span>
                Autorizo el tratamiento de mis datos para orientación de vivienda y contacto
                telefónico con Laura (CasaLista / Colsubsidio).
              </span>
            </label>

            {formError && <p className="text-sm text-red-600">{formError}</p>}

            <div className="flex flex-wrap gap-2 pt-2">
              <Button onClick={submitCall} disabled={callMutation.isPending}>
                {callMutation.isPending
                  ? 'Enviando…'
                  : mode === 'now'
                    ? 'Llamarme ahora'
                    : 'Programar llamada'}
              </Button>
              <Button variant="secondary" onClick={resetModal}>
                Cancelar
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </AppShell>
  )
}
