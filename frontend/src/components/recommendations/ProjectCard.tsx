import { ExternalLink, FileText, Heart, MapPin } from 'lucide-react'
import type { ProjectRecommendation } from '@/api/types'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'

interface ProjectCardProps {
  project: ProjectRecommendation
  onInterest?: (project: ProjectRecommendation) => void
}

export const ProjectCard = ({ project, onInterest }: ProjectCardProps) => {
  const reasons = (project.matched_factors ?? []).slice(0, 3)

  return (
    <article className="flex h-full flex-col rounded-3xl bg-white p-6 text-left surface-shadow">
      <div className="flex items-start justify-between gap-4">
        <div>
          <span className="text-sm font-bold text-[var(--color-green)]">
            #{project.rank} recomendado
          </span>
          <h2 className="mt-1 font-display text-2xl text-[var(--color-ink)]">
            {project.project_name}
          </h2>
          {(project.municipio || project.departamento) && (
            <p className="mt-2 flex items-center gap-1 text-sm text-[var(--color-muted)]">
              <MapPin size={15} aria-hidden />
              {[project.municipio, project.departamento].filter(Boolean).join(', ')}
            </p>
          )}
        </div>
        <div className="text-right">
          <Badge>{Math.round(project.compatibility_score)}%</Badge>
          <p className="mt-2 text-xs uppercase tracking-wide text-[var(--color-muted)]">
            Confianza {project.confidence}
          </p>
        </div>
      </div>

      {reasons.length > 0 && (
        <ul className="mt-5 space-y-2 text-sm text-[var(--color-muted)]">
          {reasons.map((factor) => (
            <li key={`${factor.factor}-${factor.message}`}>• {factor.message}</li>
          ))}
        </ul>
      )}

      {project.warnings && project.warnings.length > 0 && (
        <div className="mt-4 rounded-xl bg-amber-50 p-3 text-sm text-amber-900">
          {project.warnings.join(' ')}
        </div>
      )}

      <div className="mt-auto flex flex-wrap gap-2 pt-5">
        {project.brochure_url && (
          <a href={project.brochure_url} target="_blank" rel="noreferrer">
            <Button variant="secondary" className="gap-2">
              <FileText size={16} aria-hidden /> Ver brochure
            </Button>
          </a>
        )}
        {project.tour_360_url && (
          <a href={project.tour_360_url} target="_blank" rel="noreferrer">
            <Button variant="ghost" className="gap-2">
              <ExternalLink size={16} aria-hidden /> Recorrido 360
            </Button>
          </a>
        )}
        <Button
          className="gap-2"
          onClick={() => onInterest?.(project)}
          aria-label={`Me interesa el proyecto ${project.project_name}`}
        >
          <Heart size={16} aria-hidden /> Me interesa este proyecto
        </Button>
      </div>
    </article>
  )
}
