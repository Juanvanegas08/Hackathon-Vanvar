import type { LeadResponse } from '@/api/types'
import { formatCOP } from '@/utils/currency'

const labels: Record<string, string> = {
  afiliado: 'Afiliación',
  categoria_afiliacion: 'Categoría',
  personas_a_cargo: 'Grupo familiar',
  ingreso_hogar: 'Ingreso del hogar',
  ahorro: 'Ahorro',
  ubicacion_deseada: 'Zona deseada',
  plazo_compra: 'Horizonte de compra',
}

const statusFor = (
  lead: LeadResponse,
  field: string,
): 'Confirmado' | 'Por confirmar' | 'Declarado' | 'Precargado' => {
  const meta = lead.field_metadata?.[field]
  if (lead.fields_to_confirm?.includes(field) || meta?.requires_confirmation) {
    return 'Por confirmar'
  }
  if (meta?.confirmed) return 'Confirmado'
  if (meta?.source === 'user_declared') return 'Declarado'
  if (lead.prefilled_fields?.includes(field) || meta?.source === 'mock_affiliation_service') {
    return 'Precargado'
  }
  if (meta?.source === 'user_declared' || lead[field] != null) return 'Declarado'
  return 'Precargado'
}

const displayValue = (field: string, value: unknown): string => {
  if (typeof value === 'boolean') return value ? 'Sí' : 'No'
  if (typeof value === 'number' && ['ingreso_hogar', 'ahorro', 'salario_mensual'].includes(field)) {
    return formatCOP(value)
  }
  return String(value)
}

export const DetectedFacts = ({ lead }: { lead: LeadResponse }) => {
  const fields = Object.keys(labels).filter((field) => {
    const value = lead[field]
    return value !== null && value !== undefined && value !== ''
  })

  if (fields.length === 0) {
    return (
      <p className="text-sm text-[var(--color-muted)]">
        Aún estamos construyendo tu perfil.
      </p>
    )
  }

  return (
    <dl className="space-y-3 text-sm">
      {fields.map((field) => (
        <div key={field} className="flex items-start justify-between gap-3">
          <div>
            <dt className="text-[var(--color-muted)]">{labels[field]}</dt>
            <dd className="font-semibold text-[var(--color-ink)]">
              {displayValue(field, lead[field])}
            </dd>
          </div>
          <span className="rounded-full bg-[#f1f0eb] px-2 py-1 text-xs font-medium text-[var(--color-blue)]">
            {statusFor(lead, field)}
          </span>
        </div>
      ))}
    </dl>
  )
}
