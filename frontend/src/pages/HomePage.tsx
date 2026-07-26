import { useMutation } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Phone } from 'lucide-react'
import {
  lookupPhoneIdentity,
  requestPhoneCall,
  type DocumentType,
  type PhoneLookupResponse,
} from '@/api/phone.api'
import { BrochureShowcase } from '@/components/home/BrochureShowcase'
import { AmbientBackground } from '@/components/layout/AmbientBackground'
import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { TextField } from '@/components/ui/TextField'
import { getErrorMessage } from '@/utils/errors'
import heroFamilia from '@/assets/images/hero-familia.png'

type CallMode = 'now' | 'schedule'
type CallStep = 'document' | 'confirm' | 'register'

const COUNTRY_CODES = [
  { code: '57', label: 'CO +57' },
  { code: '1', label: 'US/CA +1' },
  { code: '52', label: 'MX +52' },
  { code: '51', label: 'PE +51' },
  { code: '593', label: 'EC +593' },
  { code: '58', label: 'VE +58' },
  { code: '34', label: 'ES +34' },
] as const

const toLocalInputValue = (date: Date) => {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export const HomePage = () => {
  const navigate = useNavigate()
  const [callModalOpen, setCallModalOpen] = useState(false)
  const [step, setStep] = useState<CallStep>('document')
  const [lookup, setLookup] = useState<PhoneLookupResponse | null>(null)
  const [mode, setMode] = useState<CallMode>('now')
  const [nombre, setNombre] = useState('')
  const [countryCode, setCountryCode] = useState('57')
  const [phone, setPhone] = useState('')
  const [documentType, setDocumentType] = useState<DocumentType>('CC')
  const [documentNumber, setDocumentNumber] = useState('')
  const [phoneConfirmed, setPhoneConfirmed] = useState(false)
  const [scheduledLocal, setScheduledLocal] = useState(() => {
    const d = new Date(Date.now() + 15 * 60_000)
    return toLocalInputValue(d)
  })
  const [consent, setConsent] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const minSchedule = useMemo(() => toLocalInputValue(new Date(Date.now() + 2 * 60_000)), [])

  const lookupMutation = useMutation({
    mutationFn: lookupPhoneIdentity,
    onSuccess: (result) => {
      setFormError(null)
      setLookup(result)
      if (result.nombre) {
        setNombre(result.nombre)
      }
      if (result.known_lead && result.has_phone) {
        setStep('confirm')
        setPhoneConfirmed(false)
      } else {
        setStep('register')
      }
    },
    onError: (err) => {
      setFormError(getErrorMessage(err))
    },
  })

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
    setStep('document')
    setLookup(null)
    setNombre('')
    setPhone('')
    setDocumentNumber('')
    setPhoneConfirmed(false)
    setConsent(false)
    setFormError(null)
    setSuccessMessage(null)
    lookupMutation.reset()
    callMutation.reset()
  }

  const submitLookup = () => {
    setFormError(null)
    setSuccessMessage(null)
    if (!documentNumber.trim()) {
      setFormError('Ingresa tu número de documento.')
      return
    }
    lookupMutation.mutate({
      document_type: documentType,
      document_number: documentNumber.trim(),
    })
  }

  const submitConfirmedCall = () => {
    setFormError(null)
    setSuccessMessage(null)
    if (!phoneConfirmed) {
      setFormError('Confirma que el número terminado en esos dígitos es el tuyo.')
      return
    }
    if (!consent) {
      setFormError('Debes aceptar el consentimiento de datos.')
      return
    }
    if (!nombre.trim() || nombre.trim().length < 2) {
      setFormError('Necesitamos tu nombre para continuar.')
      return
    }
    const scheduledAt =
      mode === 'schedule' ? new Date(scheduledLocal).toISOString() : undefined
    if (mode === 'schedule' && Number.isNaN(Date.parse(scheduledLocal))) {
      setFormError('La fecha programada no es válida.')
      return
    }
    callMutation.mutate({
      document_type: documentType,
      document_number: documentNumber.trim(),
      data_consent: true,
      confirm_stored_phone: true,
      nombre: nombre.trim(),
      mode,
      ...(mode === 'schedule' ? { scheduled_at: scheduledAt } : {}),
    })
  }

  const submitRegisterCall = () => {
    setFormError(null)
    setSuccessMessage(null)
    if (!nombre.trim() || !phone.trim()) {
      setFormError('Completa nombre y teléfono.')
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
      document_type: documentType,
      document_number: documentNumber.trim(),
      data_consent: true,
      confirm_stored_phone: false,
      nombre: nombre.trim(),
      country_code: countryCode,
      phone: phone.trim(),
      mode,
      ...(mode === 'schedule' ? { scheduled_at: scheduledAt } : {}),
    })
  }

  const goToRegisterInstead = () => {
    setPhoneConfirmed(false)
    setPhone('')
    setStep('register')
    setFormError(null)
  }

  const modeButtons = (
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
  )

  const scheduleField =
    mode === 'schedule' ? (
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
    ) : null

  const consentField = (
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
  )

  return (
    <AppShell>
      <section className="relative isolate overflow-visible pb-10 pt-2 sm:pb-14">
        <div
          className="hero-bubbles pointer-events-none absolute left-1/2 w-screen -translate-x-1/2"
          style={{ top: '-5.5rem', bottom: '-2rem' }}
        >
          <AmbientBackground />
        </div>

        <div className="relative z-10 grid items-center gap-5 sm:gap-7 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] lg:gap-4">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55 }}
            className="relative z-20 text-left lg:order-1 lg:pr-4"
          >
            <h1 className="max-w-xl font-display text-[1.75rem] leading-[1.15] tracking-tight text-[var(--color-ink)] sm:text-4xl lg:text-5xl">
              Tu camino a vivienda puede comenzar con una conversación.
            </h1>
            <p className="mt-3 max-w-lg text-[0.95rem] text-[var(--color-muted)] sm:mt-4 sm:text-lg">
              Cuéntanos qué buscas y te orientamos con proyectos alineados a tu perfil, listos para
              avanzar con un asesor.
            </p>
            <div className="mt-5 flex flex-col gap-3 sm:mt-7 sm:flex-row sm:flex-wrap sm:items-center">
              <Button
                className="min-h-12 w-full gap-2 px-7 text-base sm:min-h-14 sm:w-auto sm:px-8 sm:text-lg"
                onClick={() => navigate('/identification')}
              >
                Hablar ahora
              </Button>
              <Button
                variant="secondary"
                className="min-h-12 w-full gap-2 px-6 text-base sm:min-h-14 sm:w-auto sm:px-7 sm:text-lg"
                onClick={() => {
                  setSuccessMessage(null)
                  setFormError(null)
                  setCallModalOpen(true)
                }}
              >
                <Phone size={18} aria-hidden /> Prefiero que me llamen
              </Button>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.97, y: 14 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
            className="hero-photo relative mx-auto hidden w-full max-w-md lg:order-2 lg:-ml-4 lg:block lg:max-w-none"
          >
            <div className="hero-photo-glow" aria-hidden />
            <div className="hero-photo-frame">
              <img
                src={heroFamilia}
                alt="Familia disfrutando el hogar juntos"
                className="hero-photo-img"
                decoding="async"
              />
            </div>
          </motion.div>
        </div>
      </section>

      <BrochureShowcase />

      <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--color-line)] py-8 text-sm text-[var(--color-muted)]">
        <span>Colsubsidio · Orientación de vivienda</span>
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
        ) : step === 'document' ? (
          <div className="space-y-4">
            <p className="text-sm text-[var(--color-muted)]">
              Empieza con tu documento. Si ya estás en el sistema, te pediremos confirmar el
              celular registrado.
            </p>

            <div className="grid gap-3 sm:grid-cols-[7rem_1fr]">
              <label className="block text-sm font-medium text-[var(--color-ink)]">
                Documento
                <select
                  className="mt-1 w-full rounded-xl border border-[var(--color-line)] bg-white px-3 py-2"
                  value={documentType}
                  onChange={(e) => setDocumentType(e.target.value as DocumentType)}
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

            {formError && <p className="text-sm text-red-600">{formError}</p>}

            <div className="flex flex-wrap gap-2 pt-2">
              <Button onClick={submitLookup} disabled={lookupMutation.isPending}>
                {lookupMutation.isPending ? 'Buscando…' : 'Continuar'}
              </Button>
              <Button variant="secondary" onClick={resetModal}>
                Cancelar
              </Button>
            </div>
          </div>
        ) : step === 'confirm' ? (
          <div className="space-y-4">
            <p className="text-sm text-[var(--color-muted)]">
              {lookup?.message ||
                'Encontramos tu documento. Confirma el celular para que Laura te llame.'}
            </p>

            {lookup?.nombre ? (
              <p className="text-[var(--color-ink)]">
                Hola, <span className="font-medium">{lookup.nombre}</span>
              </p>
            ) : (
              <TextField
                label="Nombre completo"
                name="nombre"
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                placeholder="Como quieres que te salude Laura"
                autoComplete="name"
              />
            )}

            <div className="rounded-xl border border-[var(--color-line)] bg-white/70 px-4 py-3">
              <p className="text-sm text-[var(--color-muted)]">Celular registrado</p>
              <p className="mt-1 font-medium tracking-wide text-[var(--color-ink)]">
                ****{lookup?.phone_last4}
              </p>
            </div>

            <label className="flex items-start gap-3 text-sm text-[var(--color-ink)]">
              <input
                type="checkbox"
                className="mt-1"
                checked={phoneConfirmed}
                onChange={(e) => setPhoneConfirmed(e.target.checked)}
              />
              <span>
                Sí, ese es mi número (terminado en {lookup?.phone_last4}). Pueden llamarme ahí.
              </span>
            </label>

            {modeButtons}
            {scheduleField}
            {consentField}

            {formError && <p className="text-sm text-red-600">{formError}</p>}

            <div className="flex flex-wrap gap-2 pt-2">
              <Button onClick={submitConfirmedCall} disabled={callMutation.isPending}>
                {callMutation.isPending
                  ? 'Enviando…'
                  : mode === 'now'
                    ? 'Llamarme ahora'
                    : 'Programar llamada'}
              </Button>
              <Button variant="secondary" onClick={goToRegisterInstead}>
                No es mi número
              </Button>
              <Button
                variant="secondary"
                onClick={() => {
                  setStep('document')
                  setLookup(null)
                  setPhoneConfirmed(false)
                  setFormError(null)
                }}
              >
                Volver
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-[var(--color-muted)]">
              {lookup?.known_lead
                ? 'Ingresa el celular al que quieres que te llamemos.'
                : 'No encontramos ese documento. Registra tu nombre y celular para continuar.'}
            </p>

            <TextField
              label="Nombre completo"
              name="nombre"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder="Como quieres que te salude Laura"
              autoComplete="name"
            />

            <div className="grid gap-3 sm:grid-cols-[8.5rem_1fr]">
              <label className="block text-sm font-medium text-[var(--color-ink)]">
                Indicativo
                <select
                  className="mt-1 w-full rounded-xl border border-[var(--color-line)] bg-white px-3 py-2"
                  value={countryCode}
                  onChange={(e) => setCountryCode(e.target.value)}
                  aria-label="Indicativo de país"
                >
                  {COUNTRY_CODES.map((item) => (
                    <option key={item.code} value={item.code}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </label>
              <TextField
                label="Celular"
                name="phone"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="3001234567"
                autoComplete="tel-national"
                inputMode="tel"
              />
            </div>

            {modeButtons}
            {scheduleField}
            {consentField}

            {formError && <p className="text-sm text-red-600">{formError}</p>}

            <div className="flex flex-wrap gap-2 pt-2">
              <Button onClick={submitRegisterCall} disabled={callMutation.isPending}>
                {callMutation.isPending
                  ? 'Enviando…'
                  : mode === 'now'
                    ? 'Llamarme ahora'
                    : 'Programar llamada'}
              </Button>
              <Button
                variant="secondary"
                onClick={() => {
                  setStep('document')
                  setLookup(null)
                  setFormError(null)
                }}
              >
                Volver
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </AppShell>
  )
}
