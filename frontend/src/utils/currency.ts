const copFormatter = new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 })

export const formatCOP = (value?: number | null) => value == null ? '—' : copFormatter.format(value)
export const parseCOPInput = (value: string) => {
  const digits = value.replace(/[^\d-]/g, '')
  return digits === '' || digits === '-' ? null : Number(digits)
}
