import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getLead, getSummary, listLeads } from '@/api/leads.api'
import { getRecommendations } from '@/api/recommendations.api'
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
  buildClosingPlaybook,
  resolveLeadAffinity,
} from '@/utils/advisorBriefing'

export const AdvisorPage = () => {
  const [params, setParams] = useSearchParams()
  const selectedId = params.get('lead')
  const mockMode = isAdvisorMockEnabled(params.get('mock'))

  const setMockMode = (enabled: boolean) => {
    const next = new URLSearchParams(params)
    if (enabled) {
      next.set('mock', '1')
      if (!next.get('lead')) next.set('lead', 'mock-lead-laura')
    } else {
      // mock=0 overrides VITE_ADVISOR_MOCK so puedes volver a API real
      next.set('mock', '0')
      if (next.get('lead')?.startsWith('mock-')) next.delete('lead')
    }
    setParams(next)
  }

  const leadsQuery = useQuery({
    queryKey: ['leads', mockMode ? 'mock' : 'live'],
    queryFn: mockMode ? listMockAdvisorLeads : listLeads,
    refetchInterval: mockMode ? false : 15_000,
  })

  useEffect(() => {
    if (!mockMode || selectedId || !leadsQuery.data?.length) return
    const next = new URLSearchParams(params)
    next.set('lead', leadsQuery.data[0].id)
    if (!next.get('mock')) next.set('mock', '1')
    setParams(next, { replace: true })
  }, [mockMode, selectedId, leadsQuery.data, params, setParams])

  const detailQuery = useQuery({
    queryKey: ['advisor-detail', mockMode ? 'mock' : 'live', selectedId],
    queryFn: async () => {
      if (!selectedId) return null
      if (mockMode) return getMockAdvisorDetail(selectedId)
      const [lead, summary, recommendations] = await Promise.all([
        getLead(selectedId),
        getSummary(selectedId),
        getRecommendations(selectedId, { limit: 3 }),
      ])
      return { lead, summary, recommendations }
    },
    enabled: Boolean(selectedId),
  })

  const detail = detailQuery.data
  const topProject = detail?.recommendations.recommended_projects[0] ?? null
  const persona = detail
    ? buildBuyerPersona(detail.lead, detail.summary, topProject)
    : null
  const insights = detail
    ? buildCallInsights(detail.lead, detail.summary, topProject)
    : []
  const playbook = detail
    ? buildClosingPlaybook(detail.lead, detail.summary, topProject)
    : []
  const affinity = detail ? resolveLeadAffinity(detail.lead, topProject) : null
  const clientName = detail?.lead.nombre?.trim()
  const briefingTitle = clientName
    ? `Briefing de ${clientName}`
    : 'Briefing del cliente'

  return (
    <AppShell>
      <section className="py-8 text-left">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-green)]">
              Orquestador comercial
            </p>
            <h1 className="mt-2 font-display text-4xl md:text-5xl">
              {briefingTitle}
            </h1>
            <p className="mt-3 max-w-2xl text-[var(--color-muted)]">
              Después de la llamada, aquí tienes el briefing completo: quién es el cliente,
              qué se identificó, qué ofrecerle y cómo cerrar la venta.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant={mockMode ? 'primary' : 'secondary'}
              onClick={() => setMockMode(!mockMode)}
            >
              {mockMode ? 'Datos demo (sin backend)' : 'Ver sin backend'}
            </Button>
            <Link to="/demo">
              <Button variant="secondary">Modo demo</Button>
            </Link>
            {!mockMode && (
              <Button variant="ghost" onClick={() => void leadsQuery.refetch()}>
                Actualizar cola
              </Button>
            )}
          </div>
        </div>

        {leadsQuery.isLoading && (
          <div className="mt-10">
            <Spinner label="Cargando cola comercial" />
          </div>
        )}
        {leadsQuery.isError && !mockMode && (
          <div className="mt-10 space-y-4">
            <ErrorState
              message="No pudimos conectar con el servicio. Revisa que el backend esté en ejecución."
              onRetry={() => void leadsQuery.refetch()}
            />
            <div className="text-center">
              <Button onClick={() => setMockMode(true)}>Abrir vista con datos demo</Button>
            </div>
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

              {selectedId && detailQuery.isLoading && (
                <div className="rounded-[1.75rem] bg-white p-10">
                  <Spinner label="Preparando briefing del asesor" />
                </div>
              )}

              {selectedId && detailQuery.isError && (
                <ErrorState
                  message="No pudimos cargar el detalle del lead."
                  onRetry={() => void detailQuery.refetch()}
                />
              )}

              {detail && persona && (
                <div className="space-y-6">
                  <header className="rounded-[1.75rem] border border-[var(--color-yellow)]/50 bg-gradient-to-br from-[#fff9db] via-white to-[#f4f7fb] p-6 surface-shadow">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--color-green)]">
                          {briefingEyebrow(affinity?.band)}
                        </p>
                        <h2 className="mt-2 font-display text-3xl md:text-4xl">
                          {detail.lead.nombre ?? 'Lead sin nombre'}
                        </h2>
                        <p className="mt-2 text-lg text-[var(--color-ink)]">
                          {detail.summary.headline}
                        </p>
                        <p className="mt-3 max-w-2xl text-sm text-[var(--color-muted)]">
                          {detail.summary.disclaimer}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Badge
                          className={
                            detail.lead.afiliado === true
                              ? 'bg-[var(--color-green)]'
                              : detail.lead.afiliado === false
                                ? 'bg-[var(--color-muted)]'
                                : 'bg-[var(--color-blue)]'
                          }
                        >
                          {affiliationLabel(detail.lead)}
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

                  <div className="grid gap-6 xl:grid-cols-2">
                    <BuyerPersonaCard persona={persona} />
                    <CallInsightsCard insights={insights} />
                  </div>

                  <ClosingPlaybookCard
                    steps={playbook}
                    talkTracks={persona.talkTracks}
                    objections={persona.objections}
                  />

                  <ClientProfilePanel lead={detail.lead} summary={detail.summary} />

                  <AdvisorRecommendationsPanel
                    recommendations={detail.recommendations}
                    warning={detail.summary.recommendation_warning}
                  />
                </div>
              )}
            </div>
          </div>
        )}
      </section>
    </AppShell>
  )
}
