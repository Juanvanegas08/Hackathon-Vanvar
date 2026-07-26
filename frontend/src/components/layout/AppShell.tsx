import type { PropsWithChildren } from 'react'
import { Link } from 'react-router-dom'
import colsubsidioLogo from '@/assets/brand/colsubsidio-horizontal.png'

interface AppShellProps extends PropsWithChildren {
  showHeader?: boolean
}

export const AppShell = ({ children, showHeader = true }: AppShellProps) => (
  <div className="relative min-h-screen overflow-x-hidden bg-[var(--color-bg)] text-[var(--color-ink)]">
    <div className="relative mx-auto min-h-screen max-w-7xl px-5 sm:px-8">
      {showHeader && (
        <header className="relative z-20 flex items-center justify-between gap-4 bg-transparent py-5">
          <Link to="/" className="inline-flex items-center" aria-label="Colsubsidio - Inicio">
            <img
              src={colsubsidioLogo}
              alt="Colsubsidio"
              className="h-10 w-auto object-contain sm:h-12"
              decoding="async"
            />
          </Link>
          <nav className="flex items-center gap-5 text-sm font-medium text-[var(--color-muted)]">
            <Link to="/advisor" className="hover:text-[var(--color-ink)]">
              Asesor
            </Link>
            <Link
              to="/identification"
              className="rounded-full bg-[var(--color-ink)] px-4 py-2 text-white hover:bg-[var(--color-blue)]"
            >
              Empezar
            </Link>
          </nav>
        </header>
      )}
      <main>{children}</main>
    </div>
  </div>
)
