import type { LeadResponse } from '@/api/types'

export interface ProgressCategory {
  key: string
  label: string
  complete: number
  total: number
}

const completed = (values: readonly unknown[]) =>
  values.filter((value) => value !== null && value !== undefined && value !== '').length

export const getProfileProgress = (lead?: LeadResponse | null): ProgressCategory[] => {
  const categories: Array<{
    key: string
    label: string
    values: readonly unknown[]
  }> = [
    {
      key: 'affiliation',
      label: 'Afiliación',
      values: [lead?.afiliado, lead?.afiliacion_confirmada, lead?.categoria_afiliacion],
    },
    {
      key: 'household',
      label: 'Hogar',
      values: [lead?.personas_hogar, lead?.personas_a_cargo, lead?.tiene_vivienda],
    },
    {
      key: 'capacity',
      label: 'Capacidad orientativa',
      values: [lead?.ingreso_hogar, lead?.ahorro, lead?.obligaciones_mensuales],
    },
    {
      key: 'preferences',
      label: 'Preferencias',
      values: [lead?.ubicacion_deseada, lead?.plazo_compra, lead?.proyecto_interes],
    },
  ]

  return categories.map(({ key, label, values }) => ({
    key,
    label,
    complete: completed(values),
    total: values.length,
  }))
}
