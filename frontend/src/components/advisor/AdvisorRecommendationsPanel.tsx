import { FileText } from 'lucide-react'
import type { ProjectRecommendation, RecommendationResponse } from '@/api/types'
import { findBrochureForProject } from '@/data/brochures'
import { cn } from '@/utils/cn'

export const AdvisorRecommendationsPanel = ({
  recommendations,
  warning,
}: {
  recommendations: RecommendationResponse | null
  warning?: string | null
}) => {
  const projects = [...(recommendations?.recommended_projects ?? [])].sort(
    (a, b) => b.compatibility_score - a.compatibility_score || a.rank - b.rank,
  )

  return (
    <section className="rounded-[1.75rem] bg-white p-5 surface-shadow sm:p-6">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--color-green)]">
        Proyectos a ofrecer
      </p>
      <h3 className="mt-2 font-display text-2xl">Ordenados por afinidad</h3>
      <p className="mt-1 text-sm text-[var(--color-muted)]">
        Presenta primero el de mayor afinidad. Abre el brochure si el cliente quiere verlo.
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
        <p className="mt-5 text-sm text-[var(--color-muted)]">
          Aún no hay proyectos recomendables. Completa zona, ingresos o afiliación en la
          conversación.
        </p>
      ) : (
        <ul className="mt-5 divide-y divide-[var(--color-line)] rounded-2xl border border-[var(--color-line)]">
          {projects.map((project: ProjectRecommendation, index) => {
            const brochure = findBrochureForProject({
              projectId: project.project_id,
              canonicalId: project.canonical_project_id,
              projectName: project.project_name,
              brochureUrl: project.brochure_url,
            })
            const brochureUrl = brochure?.url ?? project.brochure_url ?? null
            const affinity = Math.round(project.compatibility_score)

            return (
              <li
                key={project.canonical_project_id}
                className="flex flex-wrap items-center gap-3 px-3 py-3 sm:flex-nowrap sm:gap-4 sm:px-4"
              >
                <span
                  className={cn(
                    'flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold',
                    index === 0
                      ? 'bg-[var(--color-yellow)] text-[var(--color-ink)]'
                      : 'bg-[#f1f0eb] text-[var(--color-muted)]',
                  )}
                >
                  {index + 1}
                </span>

                <div className="min-w-0 flex-1">
                  <p className="truncate font-semibold text-[var(--color-ink)]">
                    {project.project_name}
                  </p>
                  <p className="mt-0.5 text-xs text-[var(--color-muted)]">
                    Afinidad {affinity}%
                    {(project.municipio || project.departamento) &&
                      ` · ${[project.municipio, project.departamento].filter(Boolean).join(', ')}`}
                  </p>
                </div>

                <span className="shrink-0 rounded-full bg-[#e8f6ee] px-2.5 py-1 text-xs font-semibold text-[var(--color-green)]">
                  {affinity}%
                </span>

                {brochureUrl ? (
                  <a
                    href={brochureUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-[var(--color-line)] bg-white px-3 py-1.5 text-xs font-semibold text-[var(--color-ink)] transition hover:border-[var(--color-yellow)] hover:bg-[#fff9db]"
                  >
                    <FileText size={14} aria-hidden />
                    Ver brochure
                  </a>
                ) : (
                  <span className="shrink-0 text-xs text-[var(--color-muted)]">Sin brochure</span>
                )}
              </li>
            )
          })}
        </ul>
      )}

      {recommendations?.regulatory_context != null && (
        <div className="mt-5 rounded-2xl bg-[#f4f7fb] p-4 text-sm text-[var(--color-blue)]">
          Hay contexto regulatorio 90/10 disponible. Úsalo solo si el lead no es afiliado o
          hay duda de cupo.
        </div>
      )}
    </section>
  )
}
