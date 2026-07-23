import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { MessageCircle, Phone, Sparkles } from 'lucide-react'
import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'

const benefits = [
  {
    title: 'Conversación de pocos minutos',
    body: 'Una pregunta a la vez, sin formularios interminables.',
  },
  {
    title: 'Recomendaciones personalizadas',
    body: 'Proyectos canónicos alineados a tu perfil real.',
  },
  {
    title: 'Información lista para el asesor',
    body: 'Tu orientación llega preparada al equipo comercial.',
  },
]

export const HomePage = () => {
  const navigate = useNavigate()
  const [callModalOpen, setCallModalOpen] = useState(false)

  return (
    <AppShell>
      <section className="relative grid min-h-[78vh] items-center gap-10 pb-16 pt-4 lg:grid-cols-[1.1fr_0.9fr]">
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-left"
        >
          <p className="mb-4 text-sm font-semibold uppercase tracking-[0.2em] text-[var(--color-muted)]">
            Experiencia demostrativa
          </p>
          <h1 className="font-display text-4xl leading-[1.05] tracking-tight text-[var(--color-ink)] sm:text-6xl lg:text-7xl">
            CasaLista
          </h1>
          <p className="mt-4 max-w-xl font-display text-2xl leading-snug text-[var(--color-blue)] sm:text-3xl">
            Tu camino a vivienda puede comenzar con una conversación.
          </p>
          <p className="mt-5 max-w-lg text-lg text-[var(--color-muted)]">
            Cuéntanos lo que estás buscando y construiremos una orientación personalizada con
            proyectos acordes a tu perfil.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Button className="min-h-14 gap-2 px-7 text-lg" onClick={() => navigate('/identification')}>
              <Sparkles size={18} aria-hidden /> Hablar ahora
            </Button>
            <Button
              variant="secondary"
              className="min-h-14 gap-2 px-7 text-lg"
              onClick={() => setCallModalOpen(true)}
            >
              <Phone size={18} aria-hidden /> Prefiero que me llamen
            </Button>
          </div>
          <button
            type="button"
            className="mt-5 inline-flex items-center gap-2 text-sm font-medium text-[var(--color-blue)] underline-offset-4 hover:underline"
            onClick={() => navigate('/identification')}
          >
            <MessageCircle size={16} aria-hidden /> Prefiero continuar por texto
          </button>
          <p className="mt-10 max-w-md text-sm text-[var(--color-muted)]">
            La información se utiliza únicamente para construir una orientación personalizada. Este
            prototipo no realiza aprobaciones de crédito.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="relative hidden min-h-[420px] lg:block"
          aria-hidden
        >
          <div className="absolute inset-8 rounded-[40%] bg-[radial-gradient(circle_at_40%_35%,#fff4a8_0%,#f5c518_45%,transparent_70%)] blur-2xl" />
          <div className="absolute bottom-10 left-10 right-10 rounded-[2rem] bg-white/80 p-6 backdrop-blur surface-shadow">
            <p className="font-display text-2xl text-[var(--color-ink)]">Orientación sin fricción</p>
            <p className="mt-2 text-[var(--color-muted)]">
              Voz primero. Texto temporal. Lista para OpenAI Realtime y Twilio.
            </p>
          </div>
        </motion.div>
      </section>

      <section className="grid gap-5 border-t border-[var(--color-line)] py-14 md:grid-cols-3">
        {benefits.map((item) => (
          <div key={item.title} className="text-left">
            <h2 className="font-display text-xl text-[var(--color-ink)]">{item.title}</h2>
            <p className="mt-2 text-[var(--color-muted)]">{item.body}</p>
          </div>
        ))}
      </section>

      <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--color-line)] py-8 text-sm text-[var(--color-muted)]">
        <span>CasaLista Voice · hackathon Colsubsidio</span>
        <Link to="/demo" className="font-medium text-[var(--color-blue)] hover:underline">
          Modo demo
        </Link>
      </footer>

      <Modal
        open={callModalOpen}
        title="Llamadas próximamente"
        onClose={() => setCallModalOpen(false)}
      >
        <p className="text-[var(--color-muted)]">
          Las llamadas telefónicas estarán disponibles en la siguiente fase.
        </p>
        <div className="mt-6">
          <Button onClick={() => setCallModalOpen(false)}>Entendido</Button>
        </div>
      </Modal>
    </AppShell>
  )
}
