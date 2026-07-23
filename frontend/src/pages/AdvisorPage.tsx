import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { getLead, getSummary, listLeads } from '@/api/leads.api'
import { getRecommendations } from '@/api/recommendations.api'
import { AppShell } from '@/components/layout/AppShell'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { ErrorState } from '@/components/ui/ErrorState'
import { Spinner } from '@/components/ui/Spinner'

export const AdvisorPage = () => {
  const [params, setParams] = useSearchParams()
  const selectedId = params.get('lead')

  const leadsQuery = useQuery({
    queryKey: ['leads'],
    queryFn: listLeads,
  })

  const detailQuery = useQuery({
    queryKey: ['advisor-detail', selectedId],
    queryFn: async () => {
      if (!selectedId) return null
      const [lead, summary, recommendations] = await Promise.all([
        getLead(selectedId),
        getSummary(selectedId),
        getRecommendations(selectedId, { limit: 3 }),
      ])
      return { lead, summary, recommendations }
    },
    enabled: Boolean(selectedId),
  })

  return (
    <AppShell>
      <section className="py-8 text-left">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-4xl">Dashboard comercial</h1>
            <p className="mt-2 max-w-2xl text-[var(--color-muted)]">
              Modo demostración: los leads se eliminan al reiniciar el backend.
            </p>
          </div>
          <Link to="/demo">
            <Button variant="secondary">Modo demo</Button>
          </Link>
        </div>

        {leadsQuery.isLoading && (
          <div className="mt-10">
            <Spinner label="Cargando leads" />
          </div>
        )}
        {leadsQuery.isError && (
          <div className="mt-10">
            <ErrorState
              message="No pudimos conectar con el servicio. Revisa que el backend esté en ejecución."
              onRetry={() => void leadsQuery.refetch()}
            />
          </div>
        )}

        {leadsQuery.data && (
          <div className="mt-8 overflow-x-auto rounded-3xl bg-white surface-shadow">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-[var(--color-line)] text-[var(--color-muted)]">
                <tr>
                  <th className="px-4 py-3 font-medium">Lead</th>
                  <th className="px-4 py-3 font-medium">Estado</th>
                  <th className="px-4 py-3 font-medium">Afiliación</th>
                  <th className="px-4 py-3 font-medium">Categoría</th>
                  <th className="px-4 py-3 font-medium">Pendientes</th>
                  <th className="px-4 py-3 font-medium" />
                </tr>
              </thead>
              <tbody>
                {leadsQuery.data.map((lead) => (
                  <tr key={lead.id} className="border-b border-[var(--color-line)]/70">
                    <td className="px-4 py-3">
                      <p className="font-semibold">{lead.nombre ?? 'Sin nombre'}</p>
                      <p className="text-xs text-[var(--color-muted)]">
                        {lead.document_type} {lead.document_number}
                      </p>
                    </td>
                    <td className="px-4 py-3">{lead.estado_lead ?? lead.status ?? '—'}</td>
                    <td className="px-4 py-3">
                      {lead.afiliado == null ? '—' : lead.afiliado ? 'Sí' : 'No'}
                    </td>
                    <td className="px-4 py-3">{lead.categoria_afiliacion ?? '—'}</td>
                    <td className="px-4 py-3">{lead.fields_to_confirm?.length ?? 0}</td>
                    <td className="px-4 py-3">
                      <Button
                        variant="ghost"
                        className="min-h-0 px-3 py-1.5"
                        onClick={() => setParams({ lead: lead.id })}
                      >
                        Ver detalle
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {leadsQuery.data.length === 0 && (
              <p className="p-6 text-[var(--color-muted)]">
                Aún no hay leads en memoria. Inicia un escenario desde el modo demo.
              </p>
            )}
          </div>
        )}

        {selectedId && (
          <div className="mt-8 rounded-3xl border border-[var(--color-line)] bg-white p-6">
            {detailQuery.isLoading && <Spinner label="Cargando resumen" />}
            {detailQuery.isError && (
              <ErrorState
                message="No pudimos cargar el detalle del lead."
                onRetry={() => void detailQuery.refetch()}
              />
            )}
            {detailQuery.data && (
              <div className="space-y-6">
                <div className="flex flex-wrap items-center gap-3">
                  <h2 className="font-display text-3xl">
                    {detailQuery.data.lead.nombre ?? 'Lead sin nombre'}
                  </h2>
                  <Badge>{detailQuery.data.lead.identity_status ?? 'sin identidad'}</Badge>
                </div>
                <p className="text-lg text-[var(--color-ink)]">
                  {detailQuery.data.summary.headline}
                </p>
                <p className="text-sm text-[var(--color-muted)]">
                  {detailQuery.data.summary.disclaimer}
                </p>

                <div className="grid gap-4 md:grid-cols-3">
                  <div>
                    <h3 className="font-semibold">Confirmados</h3>
                    <ul className="mt-2 space-y-1 text-sm text-[var(--color-muted)]">
                      {detailQuery.data.summary.confirmed_fields.map((field) => (
                        <li key={field}>{field}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h3 className="font-semibold">Por confirmar</h3>
                    <ul className="mt-2 space-y-1 text-sm text-[var(--color-muted)]">
                      {(detailQuery.data.summary.fields_to_confirm.length
                        ? detailQuery.data.summary.fields_to_confirm
                        : ['Ninguno']
                      ).map((field) => (
                        <li key={field}>{field}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h3 className="font-semibold">Próxima acción</h3>
                    <p className="mt-2 text-sm text-[var(--color-muted)]">
                      {detailQuery.data.summary.next_action}
                    </p>
                  </div>
                </div>

                <div>
                  <h3 className="font-semibold">Recomendaciones</h3>
                  <ul className="mt-2 space-y-2 text-sm text-[var(--color-muted)]">
                    {detailQuery.data.recommendations.recommended_projects.map((project) => (
                      <li key={project.canonical_project_id}>
                        #{project.rank} {project.project_name} ·{' '}
                        {Math.round(project.compatibility_score)}%
                      </li>
                    ))}
                  </ul>
                </div>

                {detailQuery.data.recommendations.regulatory_context != null && (
                  <div className="rounded-2xl bg-[#f4f7fb] p-4 text-sm text-[var(--color-blue)]">
                    Contexto regulatorio 90/10 disponible en el resumen de recomendaciones.
                  </div>
                )}

                <Link to={`/results/${selectedId}`}>
                  <Button>Abrir resultados del lead</Button>
                </Link>
              </div>
            )}
          </div>
        )}
      </section>
    </AppShell>
  )
}
