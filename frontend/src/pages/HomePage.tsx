import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { MessageCircle, Phone } from 'lucide-react'
import { BrochureShowcase } from '@/components/home/BrochureShowcase'
import { AmbientBackground } from '@/components/layout/AmbientBackground'
import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'

export const HomePage = () => {
  const navigate = useNavigate()
  const [callModalOpen, setCallModalOpen] = useState(false)

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
                onClick={() => setCallModalOpen(true)}
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

      <Modal
        open={callModalOpen}
        title="Te contactamos pronto"
        onClose={() => setCallModalOpen(false)}
      >
        <p className="text-[var(--color-muted)]">
          En esta versión puedes continuar por voz o texto. La llamada telefónica estará disponible
          enseguida.
        </p>
        <div className="mt-6 flex flex-wrap gap-2">
          <Button onClick={() => navigate('/identification')}>Continuar ahora</Button>
          <Button variant="secondary" onClick={() => setCallModalOpen(false)}>
            Cerrar
          </Button>
        </div>
      </Modal>
    </AppShell>
  )
}
