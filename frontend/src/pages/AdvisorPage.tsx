import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getLead, getSummary, listAdvisorQueue } from '@/api/leads.api'
import { getRecommendations } from '@/api/recommendations.api'
import type { ProjectRecommendation, RecommendationResponse } from '@/api/types'
import { AdvisorLeadQueue } from '@/components/advisor/AdvisorLeadQueue'
import { AdvisorRecommendationsPanel } from '@/components/advisor/AdvisorRecommendationsPanel'
import { BuyerPersonaCard } from '@/components/advisor/BuyerPersonaCard'
import { CallInsightsCard } from '@/components/advisor/CallInsightsCard'
import { ClientProfilePanel } from '@/components/advisor/ClientProfilePanel'
import { ClosingPlaybookCard } from '@/components/advisor/ClosingPlaybookCard'
import { AppShell } from '@/components/layout/AppShell'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { ErrorState } from '@/components/ui/ErrorState'
import { Spinner } from '@/components/ui/Spinner'
import {
  getMockAdvisorDetail,
  isAdvisorMockEnabled,
  listMockAdvisorLeads,
} from '@/mocks/advisorMockData'
import {
  affiliationLabel,
  affinityBandClass,
  affinityBandLabel,
  briefingEyebrow,
  buildBuyerPersona,
  buildCallInsights,
  resolveLeadAffinity,
} from '@/utils/advisorBriefing'

const stubTopProject = (
  lead: {
    top_project_id?: string | null
    top_project_name?: string | null
    affinity_percent?: number | null
  } | null | undefined,
): ProjectRecommendation | null => {
  if (!lead?.top_project_id && !lead?.top_project_name) return null
  return {
    project_id: lead.top_project_id ?? 'pending',
    project_name: lead.top_project_name ?? 'Proyecto sugerido',
    canonical_project_id: lead.top_project_id ?? 'pending',
    rank: 1,
    compatibility_score: Number(lead.affinity_percent ?? 0),
    confidence: 'medium',
  }
}

export const AdvisorPage = () => {
  const [params, setParams] = useSearchParams()
  const selectedId = params.get('lead')
  const mockMode = isAdvisorMockEnabled(params.get('mock'))

  const leadsQuery = useQuery({
    queryKey: ['leads', mockMode ? 'mock' : 'advisor-queue'],
    queryFn: mockMode ? listMockAdvisorLeads : listAdvisorQueue,
    refetchInterval: mockMode ? false : 15_000,
    staleTime: 10_000,
    placeholderData: (previous) => previous,
  })

  useEffect(() => {
    if (!mockMode || selectedId || !leadsQuery.data?.length) return
    const next = new URLSearchParams(params)
    next.set('lead', leadsQuery.data[0].id)
    if (!next.get('mock')) next.set('mock', '1')
    setParams(next, { replace: true })
  }, [mockMode, selectedId, leadsQuery.data, params, setParams])

  const mockDetailQuery = useQuery({
    queryKey: ['advisor-detail', 'mock', selectedId],
    queryFn: async () => {
      if (!selectedId) return null
      return getMockAdvisorDetail(selectedId)
    },
    enabled: Boolean(selectedId) && mockMode,
  })

  const leadQuery = useQuery({
    queryKey: ['advisor-lead', selectedId],
    queryFn: () => getLead(selectedId!),
    enabled: Boolean(selectedId) && !mockMode,
    staleTime: 30_000,
  })

  const summaryQuery = useQuery({
    queryKey: ['advisor-summary', selectedId],
    queryFn: () => getSummary(selectedId!, { includeRecommendations: false }),
    enabled: Boolean(selectedId) && !mockMode,
    staleTime: 30_000,
  })

  const recommendationsQuery = useQuery({
    queryKey: ['advisor-recommendations', selectedId],
    queryFn: () =>
      getRecommendations(selectedId!, {
        limit: 3,
        // Dashboard del asesor: motor local para respuesta inmediata.
        preferOpenai: false,
      }),
    enabled: Boolean(selectedId) && !mockMode,
    staleTime: 60_000,
  })

  const lead = mockMode ? mockDetailQuery.data?.lead : leadQuery.data
  const summary = mockMode ? mockDetailQuery.data?.summary : summaryQuery.data
  const recommendations: RecommendationResponse | null | undefined = mockMode
    ? mockDetailQuery.data?.recommendations
    : recommendationsQuery.data

  const topProject =
    recommendations?.recommended_projects[0] ?? stubTopProject(lead) ?? null
  const persona = lead && summary ? buildBuyerPersona(lead, summary, topProject) : null
  const insights =
    lead && summary ? buildCallInsights(lead, summary, topProject) : []
  const affinity = lead ? resolveLeadAffinity(lead, topProject) : null

  const detailLoading = mockMode
    ? mockDetailQuery.isLoading
    : Boolean(selectedId) && leadQuery.isLoading
  const detailError = mockMode
    ? mockDetailQuery.isError
    : leadQuery.isError || summaryQuery.isError
  const retryDetail = () => {
    if (mockMode) {
      void mockDetailQuery.refetch()
      return
    }
    void leadQuery.refetch()
    void summaryQuery.refetch()
    void recommendationsQuery.refetch()
  }

  return (
    <AppShell>
      <section className="py-8 text-left">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-green)]">
              Orquestador comercial
            </p>
            <h1 className="mt-2 font-display text-4xl md:text-5xl">
              Briefing comercial
            </h1>
            <p className="mt-3 max-w-2xl text-[var(--color-muted)]">
              Después de la llamada, aquí tienes el briefing completo: quién es el cliente,
              qué se identificó, qué ofrecerle y cómo cerrar la venta.
            </p>
          </div>
          {!mockMode && (
            <Button variant="ghost" onClick={() => void leadsQuery.refetch()}>
              Actualizar cola
            </Button>
          )}
        </div>

        {leadsQuery.isLoading && !leadsQuery.data && (
          <div className="mt-8 grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
            <aside className="rounded-[1.75rem] border border-[var(--color-line)] bg-white p-4 surface-shadow">
              <div className="mb-4 flex items-center justify-between gap-2">
                <h2 className="font-display text-xl">Cola de leads</h2>
              </div>
              <Spinner label="Cargando cola" />
            </aside>
            <div className="rounded-[1.75rem] border border-dashed border-[var(--color-line)] bg-white/70 p-10 text-center">
              <p className="text-sm text-[var(--color-muted)]">
                Preparando el briefing…
              </p>
            </div>
          </div>
        )}
        {leadsQuery.isError && !mockMode && (
          <div className="mt-10">
            <ErrorState
              message="No pudimos conectar con el servicio. Revisa que el backend esté en ejecución."
              onRetry={() => void leadsQuery.refetch()}
            />
          </div>
        )}

        {leadsQuery.data && (
          <div className="mt-8 grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
            <AdvisorLeadQueue
              leads={leadsQuery.data}
              selectedId={selectedId}
              onSelect={(leadId) => {
                const next = new URLSearchParams(params)
                next.set('lead', leadId)
                setParams(next)
              }}
            />

            <div className="min-w-0">
              {!selectedId && (
                <div className="rounded-[1.75rem] border border-dashed border-[var(--color-line)] bg-white/70 p-10 text-center">
                  <h2 className="font-display text-2xl">Selecciona un lead</h2>
                  <p className="mx-auto mt-2 max-w-md text-sm text-[var(--color-muted)]">
                    Elige un cliente de la cola para ver el briefing post-llamada y el
                    guión de cierre.
                  </p>
                </div>
              )}

              {selectedId && detailLoading && (
                <div className="rounded-[1.75rem] bg-white p-10">
                  <Spinner label="Preparando briefing del asesor" />
                </div>
              )}

              {selectedId && detailError && !lead && (
                <ErrorState
                  message="No pudimos cargar el detalle del lead."
                  onRetry={retryDetail}
                />
              )}

              {lead && (
                <div className="space-y-6">
                  <header className="rounded-[1.75rem] border border-[var(--color-yellow)]/50 bg-gradient-to-br from-[#fff9db] via-white to-[#f4f7fb] p-6 surface-shadow">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--color-green)]">
                          {briefingEyebrow(affinity?.band)}
                        </p>
                        <h2 className="mt-2 font-display text-3xl md:text-4xl">
                          {lead.nombre ?? 'Lead sin nombre'}
                        </h2>
                        <p className="mt-2 text-lg text-[var(--color-ink)]">
                          {summary?.headline ?? 'Cargando resumen del perfil…'}
                        </p>
                        {summary?.disclaimer && (
                          <p className="mt-3 max-w-2xl text-sm text-[var(--color-muted)]">
                            {summary.disclaimer}
                          </p>
                        )}
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Badge
                          className={
                            lead.afiliado === true
                              ? 'bg-[var(--color-green)]'
                              : lead.afiliado === false
                                ? 'bg-[var(--color-muted)]'
                                : 'bg-[var(--color-blue)]'
                          }
                        >
                          {affiliationLabel(lead)}
                        </Badge>
                        <Badge className="bg-[var(--color-blue)]">
                          {affinity?.percent != null
                            ? `Afinidad ${Math.round(affinity.percent)}%`
                            : 'Afinidad —'}
                        </Badge>
                        <Badge className={affinityBandClass(affinity?.band)}>
                          {affinityBandLabel(affinity?.band)}
                        </Badge>
                      </div>
                    </div>

                    {!mockMode && (
                      <div className="mt-5 flex flex-wrap gap-2">
                        <Link to={`/results/${selectedId}`}>
                          <Button variant="secondary">Ver vista del cliente</Button>
                        </Link>
                        <Link to={`/conversation/${selectedId}`}>
                          <Button variant="ghost">Reabrir conversación</Button>
                        </Link>
                      </div>
                    )}
                  </header>

                  {!summary && summaryQuery.isLoading && (
                    <div className="rounded-[1.75rem] bg-white p-6">
                      <Spinner label="Cargando hallazgos de la llamada" />
                    </div>
                  )}

                  {persona && summary && (
                    <>
                      <div className="grid gap-6 xl:grid-cols-2">
                        <BuyerPersonaCard persona={persona} />
                        <CallInsightsCard insights={insights} />
                      </div>

                      <ClosingPlaybookCard lead={lead} />

                      <ClientProfilePanel lead={lead} summary={summary} />
                    </>
                  )}

                  {recommendationsQuery.isLoading && !recommendations && (
                    <div className="rounded-[1.75rem] bg-white p-6">
                      <Spinner label="Cargando proyectos recomendados" />
                    </div>
                  )}

                  {(recommendations || recommendationsQuery.isError) && (
                    <AdvisorRecommendationsPanel
                      recommendations={recommendations ?? null}
                      warning={
                        recommendationsQuery.isError
                          ? 'No pudimos cargar recomendaciones ahora. El resto del briefing ya está listo.'
                          : summary?.recommendation_warning
                      }
                    />
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </section>
    </AppShell>
  )
}
