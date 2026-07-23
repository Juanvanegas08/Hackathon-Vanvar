export interface QuestionOption {
  value: string
  label: string
}

/** Values must match backend CreditSituation enum. */
export const situacionCrediticiaOptions: QuestionOption[] = [
  { value: 'sin_reportes', label: 'Sin reportes' },
  { value: 'al_dia', label: 'Al día' },
  { value: 'atrasos_menores', label: 'Atrasos menores' },
  { value: 'atrasos_mayores', label: 'Atrasos mayores' },
  { value: 'en_proceso_normalizacion', label: 'En normalización' },
  { value: 'desconocida', label: 'No estoy seguro(a)' },
]

/** Values must match backend PurchaseTimeline enum. */
export const plazoCompraOptions: QuestionOption[] = [
  { value: 'inmediato', label: 'De inmediato' },
  { value: '3_meses', label: 'En unos 3 meses' },
  { value: '6_meses', label: 'En unos 6 meses' },
  { value: '12_meses', label: 'En unos 12 meses' },
  { value: 'mas_de_un_ano', label: 'Más de un año' },
  { value: 'no_definido', label: 'Aún no lo defino' },
]

export const optionsForField = (field: string): QuestionOption[] => {
  if (field === 'situacion_crediticia') return situacionCrediticiaOptions
  if (field === 'plazo_compra') return plazoCompraOptions
  return []
}
