import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { listDemoIdentities } from '@/api/identity.api'
import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/Button'
import { ErrorState } from '@/components/ui/ErrorState'
import { Spinner } from '@/components/ui/Spinner'
import { useFlowStore } from '@/store/flowStore'

const fallbackScenarios = [
  {
    name: 'Laura Demo',
    document_number: '1000000001',
    document_type: 'CC',
    scenario: 'Afiliada conocida',
    goal: 'Precarga, confirmaciones, conversación corta y recomendaciones.',
  },
  {
    name: 'Escenario no afiliado',
    document_number: '1000000005',
    document_type: 'CC',
    scenario: 'No afiliado conocido',
    goal: 'Mostrar contexto del 10% sin descartar al lead.',
  },
  {
    name: 'Lead nuevo',
    document_number: '9999999999',
    document_type: 'CC',
    scenario: 'Lead nuevo',
    goal: 'Construir perfil desde cero con el flujo completo.',
  },
]

export const DemoPage = () => {
  const navigate = useNavigate()
  const { setDocument, setLookup, reset } = useFlowStore()

  const demoQuery = useQuery({
    queryKey: ['demo-identities'],
    queryFn: listDemoIdentities,
    retry: false,
  })

  const scenarios = (demoQuery.data ?? []).length
    ? (demoQuery.data ?? []).map((item) => ({
        ...item,
        goal:
          item.document_number === '1000000001'
            ? 'Precarga, confirmaciones, conversación corta y recomendaciones.'
            : item.document_number === '1000000005'
              ? 'Mostrar contexto del 10% sin descartar al lead.'
              : 'Construir perfil desde cero con el flujo completo.',
      }))
    : fallbackScenarios

  const startScenario = (documentType: string, documentNumber: string) => {
    reset()
    setDocument(documentType, documentNumber)
    setLookup(null)
    navigate('/identification')
  }

  return (
    <AppShell>
      <section className="py-10 text-left">
        <h1 className="font-display text-4xl sm:text-5xl">Modo demo para el jurado</h1>
        <p className="mt-4 max-w-2xl text-lg text-[var(--color-muted)]">
          Elige un escenario. Usa el mismo flujo real de la experiencia — sin lógica paralela.
        </p>
        <p className="mt-3 text-sm text-[var(--color-muted)]">
          Los perfiles utilizados en esta demostración son completamente ficticios.
        </p>

        {demoQuery.isLoading && (
          <div className="mt-8">
            <Spinner label="Cargando escenarios" />
          </div>
        )}
        {demoQuery.isError && (
          <div className="mt-8">
            <ErrorState
              message="No pudimos cargar identidades desde el backend. Mostramos escenarios de respaldo."
              onRetry={() => void demoQuery.refetch()}
            />
          </div>
        )}

        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {scenarios
            .filter((item) =>
              ['1000000001', '1000000005', '9999999999'].includes(item.document_number),
            )
            .map((item, index) => (
              <article
                key={item.document_number}
                className="flex flex-col rounded-[2rem] bg-white p-6 text-left surface-shadow"
              >
                <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[var(--color-green)]">
                  Escenario {index + 1}
                </p>
                <h2 className="mt-3 font-display text-2xl">{item.scenario}</h2>
                <p className="mt-2 text-sm text-[var(--color-muted)]">{item.name}</p>
                <p className="mt-1 font-semibold">
                  {item.document_type} {item.document_number}
                </p>
                <p className="mt-4 flex-1 text-[var(--color-muted)]">{item.goal}</p>
                <Button
                  className="mt-6 w-full"
                  onClick={() => startScenario(item.document_type, item.document_number)}
                >
                  Iniciar escenario
                </Button>
              </article>
            ))}
        </div>
      </section>
    </AppShell>
  )
}
