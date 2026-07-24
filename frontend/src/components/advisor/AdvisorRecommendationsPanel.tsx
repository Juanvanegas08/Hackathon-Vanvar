import type { ProjectRecommendation, RecommendationResponse } from '@/api/types'
import { ProjectCard } from '@/components/recommendations/ProjectCard'

export const AdvisorRecommendationsPanel = ({
  recommendations,
  warning,
}: {
  recommendations: RecommendationResponse | null
  warning?: string | null
}) => {
  const projects = recommendations?.recommended_projects ?? []

  return (
    <section className="rounded-[1.75rem] bg-white p-6 surface-shadow">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--color-green)]">
        Proyectos a ofrecer
      </p>
      <h3 className="mt-2 font-display text-2xl">Recomendaciones para el cierre</h3>
      <p className="mt-2 text-sm text-[var(--color-muted)]">
        Presenta primero el #1. Usa el #2 solo como alternativa o contraste.
      </p>

      {warning && (
        <div className="mt-4 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-900">
          {warning}
        </div>
      )}

      {recommendations?.spoken_summary && (
        <div className="mt-4 rounded-2xl bg-[#fff9db] px-4 py-3 text-sm text-[var(--color-ink)]">
          <p className="font-semibold">Resumen hablable</p>
          <p className="mt-1">{recommendations.spoken_summary}</p>
        </div>
      )}

      {projects.length === 0 ? (
        <p className="mt-6 text-sm text-[var(--color-muted)]">
          Aún no hay proyectos recomendables. Completa zona, ingresos o afiliación en la
          conversación.
        </p>
      ) : (
        <div className="mt-6 grid gap-4 lg:grid-cols-3">
          {projects.map((project: ProjectRecommendation) => (
            <ProjectCard key={project.canonical_project_id} project={project} />
          ))}
        </div>
      )}

      {recommendations?.regulatory_context != null && (
        <div className="mt-6 rounded-2xl bg-[#f4f7fb] p-4 text-sm text-[var(--color-blue)]">
          Hay contexto regulatorio 90/10 disponible. Úsalo solo si el lead no es afiliado o
          hay duda de cupo.
        </div>
      )}
    </section>
  )
}
