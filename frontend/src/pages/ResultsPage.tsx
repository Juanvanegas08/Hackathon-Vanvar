import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { evaluateLead, getLead, getSummary } from '@/api/leads.api'
import { getRecommendations } from '@/api/recommendations.api'
import { ProjectCard } from '@/components/recommendations/ProjectCard'
import { LauraRecommendationSpeech } from '@/components/recommendations/LauraRecommendationSpeech'
import { EngagementBadge } from '@/components/conversation/EngagementBadge'
import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/Button'
import { ErrorState } from '@/components/ui/ErrorState'
import { Modal } from '@/components/ui/Modal'
import { Spinner } from '@/components/ui/Spinner'
import type { ProjectRecommendation } from '@/api/types'

export const ResultsPage = () => {
  const { leadId = '' } = useParams()
  const navigate = useNavigate()
  const [interestProject, setInterestProject] = useState<ProjectRecommendation | null>(null)
  const [actionModal, setActionModal] = useState<'asesor' | 'ruta' | null>(null)

  const readinessQuery = useQuery({
    queryKey: ['evaluate', leadId],
    queryFn: () => evaluateLead(leadId),
    enabled: Boolean(leadId),
  })

  const recommendationsQuery = useQuery({
    queryKey: ['recommendations', leadId],
    queryFn: () => getRecommendations(leadId, { limit: 3 }),
    enabled: Boolean(leadId),
  })

  const summaryQuery = useQuery({
    queryKey: ['summary', leadId],
    queryFn: () => getSummary(leadId),
    enabled: Boolean(leadId),
  })

  const leadQuery = useQuery({
    queryKey: ['lead', leadId],
    queryFn: () => getLead(leadId),
    enabled: Boolean(leadId),
  })

  const loading =
    readinessQuery.isLoading || recommendationsQuery.isLoading
  const error = readinessQuery.error || recommendationsQuery.error

  const readiness = readinessQuery.data
  const recommendations = recommendationsQuery.data
  const projects = recommendations?.recommended_projects ?? []
  const uniqueCanonical = new Set(projects.map((item) => item.canonical_project_id))
  const affiliated = summaryQuery.data?.affiliation
    ? ((summaryQuery.data.affiliation as { is_affiliated?: boolean | null }).is_affiliated ??
      null)
    : null

  const readyForAdvisor =
    readiness?.status === 'listo_para_asesor' ||
    (readiness?.readiness_score ?? 0) >= 70

  if (loading) {
    return (
      <AppShell>
        <div className="grid min-h-[60vh] place-items-center">
          <Spinner label="Estamos preparando tus mejores opciones" />
        </div>
      </AppShell>
    )
  }

  if (error) {
    const detail =
      error instanceof Error && error.message
        ? error.message
        : 'Revisa que el backend esté en ejecución.'
    return (
      <AppShell>
        <div className="mx-auto max-w-lg py-16">
          <ErrorState
            message={`No pudimos generar tus recomendaciones. ${detail}`}
            onRetry={() => {
              void readinessQuery.refetch()
              void recommendationsQuery.refetch()
              void summaryQuery.refetch()
            }}
          />
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell>
      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="py-8 text-left"
      >
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--color-green)]">
          Resultados orientativos
        </p>
        <h1 className="mt-3 max-w-3xl font-display text-4xl leading-tight sm:text-5xl">
          Encontramos opciones que pueden ajustarse a ti.
        </h1>
        <p className="mt-4 max-w-2xl text-[var(--color-muted)]">
          Este resultado es orientativo y no constituye una aprobación de crédito hipotecario.
        </p>

        <div className="mt-6 max-w-xl">
          <EngagementBadge lead={leadQuery.data} />
        </div>

        <div className="mt-8 grid gap-4 md:grid-cols-3">
          <div className="rounded-3xl bg-white p-5 surface-shadow">
            <p className="text-sm text-[var(--color-muted)]">Preparación</p>
            <p className="mt-2 font-display text-4xl">{readiness?.readiness_score ?? '—'}</p>
          </div>
          <div className="rounded-3xl bg-white p-5 surface-shadow">
            <p className="text-sm text-[var(--color-muted)]">Confianza</p>
            <p className="mt-2 font-display text-3xl capitalize">{readiness?.confidence}</p>
          </div>
          <div className="rounded-3xl bg-white p-5 surface-shadow">
            <p className="text-sm text-[var(--color-muted)]">Estado</p>
            <p className="mt-2 font-display text-2xl">{readiness?.status}</p>
          </div>
        </div>

        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          <div className="rounded-3xl border border-[var(--color-line)] bg-white/80 p-5">
            <h2 className="font-display text-xl">Factores positivos</h2>
            <ul className="mt-3 space-y-2 text-[var(--color-muted)]">
              {(readiness?.positive_factors ?? []).slice(0, 4).map((item) => (
                <li key={item}>• {item}</li>
              ))}
            </ul>
          </div>
          <div className="rounded-3xl border border-[var(--color-line)] bg-white/80 p-5">
            <h2 className="font-display text-xl">Brecha principal</h2>
            <p className="mt-3 text-[var(--color-muted)]">
              {(readiness?.gaps ?? [])[0] ?? 'Sin brechas críticas detectadas.'}
            </p>
            <p className="mt-4 text-sm font-semibold text-[var(--color-blue)]">
              Próxima acción: {readiness?.next_action}
            </p>
          </div>
        </div>

        {affiliated === false && (
          <div className="mt-6 rounded-3xl bg-[var(--color-blue)] px-5 py-4 text-white">
            También encontramos opciones compatibles para ti. La continuidad comercial está sujeta a
            la disponibilidad destinada a compradores no afiliados.
          </div>
        )}

        <div className="mt-10">
          <div className="mb-4 flex items-end justify-between gap-3">
            <h2 className="font-display text-3xl">Proyectos sugeridos</h2>
            <p className="text-sm text-[var(--color-muted)]">
              {uniqueCanonical.size} canónicos · sin duplicados
              {recommendations?.engine ? ` · motor ${recommendations.engine}` : ''}
            </p>
          </div>

          {recommendations?.spoken_summary && (
            <LauraRecommendationSpeech
              spokenSummary={recommendations.spoken_summary}
              brochureUrl={projects[0]?.brochure_url}
              projectName={projects[0]?.project_name}
              autoPlay
            />
          )}

          <div className="grid gap-5 lg:grid-cols-3">
            {projects.map((project) => (
              <ProjectCard
                key={project.canonical_project_id}
                project={project}
                onInterest={setInterestProject}
              />
            ))}
          </div>
        </div>

        <div className="mt-10 flex flex-wrap gap-3">
          {readyForAdvisor ? (
            <Button className="min-h-14 text-lg" onClick={() => setActionModal('asesor')}>
              Agendar conversación con un asesor
            </Button>
          ) : (
            <Button className="min-h-14 text-lg" onClick={() => setActionModal('ruta')}>
              Crear mi ruta para acercarme a la vivienda
            </Button>
          )}
          <Button variant="secondary" onClick={() => navigate(`/advisor?lead=${leadId}`)}>
            Ver vista del asesor
          </Button>
          <Link to="/demo">
            <Button variant="ghost">Probar otro escenario</Button>
          </Link>
        </div>
      </motion.section>

      <Modal
        open={Boolean(interestProject)}
        title="Interés registrado"
        onClose={() => setInterestProject(null)}
      >
        <p className="text-[var(--color-muted)]">
          Registramos tu interés en{' '}
          <strong className="text-[var(--color-ink)]">{interestProject?.project_name}</strong>. En
          una fase posterior, un asesor dará seguimiento.
        </p>
        <div className="mt-6">
          <Button onClick={() => setInterestProject(null)}>Continuar</Button>
        </div>
      </Modal>

      <Modal
        open={actionModal !== null}
        title={actionModal === 'asesor' ? 'Agenda simulada' : 'Ruta de nutrición'}
        onClose={() => setActionModal(null)}
      >
        <p className="text-[var(--color-muted)]">
          {actionModal === 'asesor'
            ? 'Simulamos el agendamiento con un asesor. La integración real llegará después.'
            : 'Creamos una ruta orientativa para acercarte a vivienda. Esta acción es demostrativa.'}
        </p>
        <div className="mt-6">
          <Button onClick={() => setActionModal(null)}>Perfecto</Button>
        </div>
      </Modal>
    </AppShell>
  )
}
