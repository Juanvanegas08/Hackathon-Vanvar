import type { LeadUpdate, NextQuestion } from '@/api/types'
import { parseCOPInput } from '@/utils/currency'

export type ConfirmationPayload = Record<string, { confirmed: boolean; new_value?: unknown }>
export type AnswerPayload = LeadUpdate | ConfirmationPayload

const CURRENCY_FIELDS = new Set([
  'salario_mensual',
  'ingreso_hogar',
  'ahorro',
  'obligaciones_mensuales',
])

const INTEGER_FIELDS = new Set(['personas_hogar', 'personas_a_cargo', 'beneficiarios_registrados'])

const coerceValue = (field: string, answer: unknown, type: NextQuestion['type']): unknown => {
  if (type === 'currency' || CURRENCY_FIELDS.has(field)) {
    if (typeof answer === 'number') return answer
    if (typeof answer === 'string') return parseCOPInput(answer)
  }
  if (type === 'integer' || INTEGER_FIELDS.has(field)) {
    if (typeof answer === 'number') return answer
    if (typeof answer === 'string') return Number(answer.replace(/\D/g, ''))
  }
  if (type === 'boolean' || type === 'consent') return Boolean(answer)
  return answer
}

export const adaptAnswer = (question: NextQuestion, answer: unknown): AnswerPayload => {
  if (question.type === 'confirmation') {
    const confirmed = answer === true || answer === 'yes'
    if (confirmed) {
      return { [question.field]: { confirmed: true } }
    }
    const inferredType: NextQuestion['type'] = CURRENCY_FIELDS.has(question.field)
      ? 'currency'
      : INTEGER_FIELDS.has(question.field)
        ? 'integer'
        : 'text'
    return {
      [question.field]: {
        confirmed: false,
        new_value: coerceValue(question.field, answer, inferredType),
      },
    }
  }

  return {
    [question.field]: coerceValue(question.field, answer, question.type),
  } as LeadUpdate
}

export const isConfirmationPayload = (payload: AnswerPayload): payload is ConfirmationPayload =>
  Object.values(payload).some(
    (value) => typeof value === 'object' && value !== null && 'confirmed' in value,
  )
