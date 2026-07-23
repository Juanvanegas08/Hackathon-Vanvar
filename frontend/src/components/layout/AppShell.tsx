import type { PropsWithChildren } from 'react'
import { Link } from 'react-router-dom'
import { AmbientBackground } from '@/components/layout/AmbientBackground'
import { Badge } from '@/components/ui/Badge'

interface AppShellProps extends PropsWithChildren {
  showHeader?: boolean
}

export const AppShell = ({ children, showHeader = true }: AppShellProps) => (
  <div className="relative min-h-screen overflow-hidden bg-[var(--color-bg)] text-[var(--color-ink)]">
    <AmbientBackground />
    <div className="relative mx-auto min-h-screen max-w-7xl px-5 sm:px-8">
      {showHeader && (
        <header className="flex items-center justify-between gap-4 py-6">
          <Link to="/" className="font-display text-2xl font-bold tracking-tight text-[var(--color-blue)]">
            CasaLista <span className="text-[var(--color-ink)]">Voice</span>
          </Link>
          <div className="flex items-center gap-3">
            <Badge>Experiencia demostrativa</Badge>
            <Link
              to="/demo"
              className="text-sm font-medium text-[var(--color-muted)] hover:text-[var(--color-blue)]"
            >
              Modo demo
            </Link>
          </div>
        </header>
      )}
      <main>{children}</main>
    </div>
  </div>
)
