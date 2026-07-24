import type { ReactNode } from 'react'
import type { AdvisorSummaryResponse, LeadResponse } from '@/api/types'
import { fieldLabel } from '@/utils/advisorBriefing'
import { formatCOP } from '@/utils/currency'

const money = (value: unknown) =>
  typeof value === 'number' ? formatCOP(value) : '—'

const boolLabel = (value: unknown) => {
  if (value === true) return 'Sí'
  if (value === false) return 'No'
  return '—'
}

export const ClientProfilePanel = ({
  lead,
  summary,
}: {
  lead: LeadResponse
  summary: AdvisorSummaryResponse
}) => {
  const financial = summary.financial_profile ?? {}
  const household = summary.household ?? {}
  const affiliation = summary.affiliation ?? {}
  const isAffiliated = affiliation.is_affiliated as boolean | null | undefined
  const affiliationCategory = affiliation.category as string | null | undefined
  const affiliationConfirmed = affiliation.confirmed as boolean | null | undefined

  return (
    <section className="rounded-[1.75rem] bg-white p-6 surface-shadow">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--color-green)]">
        Perfil del cliente
      </p>
      <h3 className="mt-2 font-display text-2xl">Información consolidada</h3>

      <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <InfoBlock title="Contacto">
          <Row label="Nombre" value={lead.nombre ?? '—'} />
          <Row label="Documento" value={`${lead.document_type ?? 'CC'} ${lead.document_number ?? '—'}`} />
          <Row label="Teléfono" value={lead.telefono ?? '—'} />
          <Row label="Correo" value={lead.correo ?? '—'} />
          <Row label="Canal" value={String(summary.basic_data?.canal_origen ?? lead.canal_origen ?? '—')} />
        </InfoBlock>

        <InfoBlock title="Afiliación">
          <Row
            label="Afiliado"
            value={isAffiliated == null ? '—' : isAffiliated ? 'Sí' : 'No'}
          />
          <Row
            label="Categoría"
            value={String(affiliationCategory ?? lead.categoria_afiliacion ?? '—')}
          />
          <Row
            label="Confirmada"
            value={boolLabel(affiliationConfirmed ?? lead.afiliacion_confirmada)}
          />
          <Row label="Empresa" value={lead.empresa ?? '—'} />
        </InfoBlock>

        <InfoBlock title="Finanzas">
          <Row label="Salario" value={money(financial.personal_income)} />
          <Row label="Ingreso hogar" value={money(financial.household_income)} />
          <Row label="Ahorro" value={money(financial.savings)} />
          <Row label="Obligaciones" value={money(financial.monthly_obligations)} />
        </InfoBlock>

        <InfoBlock title="Hogar y vivienda">
          <Row label="Personas hogar" value={String(household.personas_hogar ?? '—')} />
          <Row label="A cargo" value={String(household.personas_a_cargo ?? '—')} />
          <Row label="Tiene vivienda" value={boolLabel(household.tiene_vivienda)} />
          <Row label="Situación crediticia" value={lead.situacion_crediticia?.replaceAll('_', ' ') ?? '—'} />
        </InfoBlock>

        <InfoBlock title="Intención de compra">
          <Row label="Zona deseada" value={lead.ubicacion_deseada ?? '—'} />
          <Row label="Plazo" value={lead.plazo_compra?.replaceAll('_', ' ') ?? '—'} />
          <Row label="Proyecto interés" value={lead.proyecto_interes ?? '—'} />
          <Row
            label="Preferencias"
            value={lead.preferencias?.length ? lead.preferencias.join(', ') : '—'}
          />
        </InfoBlock>

        <InfoBlock title="Estado de datos">
          <Row
            label="Confirmados"
            value={
              summary.confirmed_fields.length
                ? summary.confirmed_fields.map(fieldLabel).join(', ')
                : 'Ninguno marcado'
            }
          />
          <Row
            label="Por confirmar"
            value={
              summary.fields_to_confirm.length
                ? summary.fields_to_confirm.map(fieldLabel).join(', ')
                : 'Ninguno'
            }
          />
          <Row
            label="Brechas"
            value={summary.gaps.length ? summary.gaps.join(' · ') : 'Sin brechas críticas'}
          />
        </InfoBlock>
      </div>
    </section>
  )
}

const InfoBlock = ({
  title,
  children,
}: {
  title: string
  children: ReactNode
}) => (
  <div className="rounded-2xl border border-[var(--color-line)] p-4">
    <h4 className="text-sm font-semibold text-[var(--color-ink)]">{title}</h4>
    <dl className="mt-3 space-y-2">{children}</dl>
  </div>
)

const Row = ({ label, value }: { label: string; value: string }) => (
  <div>
    <dt className="text-[11px] uppercase tracking-wide text-[var(--color-muted)]">{label}</dt>
    <dd className="text-sm text-[var(--color-ink)]">{value}</dd>
  </div>
)
