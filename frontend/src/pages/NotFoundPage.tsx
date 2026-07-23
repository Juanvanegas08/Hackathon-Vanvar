import { Link } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/Button'

export const NotFoundPage = () => (
  <AppShell>
    <section className="mx-auto flex min-h-[60vh] max-w-xl flex-col justify-center text-left">
      <h1 className="font-display text-5xl">No encontramos esta página</h1>
      <p className="mt-4 text-[var(--color-muted)]">
        Puede que el enlace haya cambiado o que la sesión de demostración ya no exista.
      </p>
      <div className="mt-8 flex gap-3">
        <Link to="/">
          <Button>Volver al inicio</Button>
        </Link>
        <Link to="/demo">
          <Button variant="secondary">Modo demo</Button>
        </Link>
      </div>
    </section>
  </AppShell>
)
