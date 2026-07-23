import { useState } from 'react'
import type { NextQuestion } from '@/api/types'
import { Button } from '@/components/ui/Button'
import { TextField } from '@/components/ui/TextField'
import { optionsForField } from '@/utils/questionOptions'
import { formatCOP } from '@/utils/currency'

interface AnswerControlsProps {
  question: NextQuestion
  onAnswer: (answer: string | boolean | number) => void
  disabled?: boolean
}

export const AnswerControls = ({ question, onAnswer, disabled = false }: AnswerControlsProps) => {
  const [value, setValue] = useState('')
  const [updating, setUpdating] = useState(false)

  if (question.type === 'boolean' || question.type === 'consent') {
    return (
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Button disabled={disabled} className="min-h-14 text-lg" onClick={() => onAnswer(true)}>
          Sí
        </Button>
        <Button
          disabled={disabled}
          variant="secondary"
          className="min-h-14 text-lg"
          onClick={() => onAnswer(false)}
        >
          No
        </Button>
      </div>
    )
  }

  if (question.type === 'confirmation' && !updating) {
    return (
      <div className="flex flex-col gap-3 sm:flex-row">
        <Button disabled={disabled} className="min-h-14 flex-1 text-lg" onClick={() => onAnswer('yes')}>
          Sí, sigue correcto
        </Button>
        <Button
          disabled={disabled}
          variant="secondary"
          className="min-h-14 flex-1 text-lg"
          onClick={() => setUpdating(true)}
        >
          No, quiero actualizarlo
        </Button>
      </div>
    )
  }

  if (question.type === 'confirmation' && updating) {
    const isCurrency = typeof question.current_value === 'number' && question.field.includes('salario')
      || question.field.includes('ahorro')
      || question.field.includes('ingreso')
      || question.field.includes('obligacion')
    const isInteger = question.field.includes('personas')
    return (
      <form
        className="flex flex-col gap-3 sm:flex-row"
        onSubmit={(event) => {
          event.preventDefault()
          if (!value.trim()) return
          if (isCurrency || isInteger) {
            onAnswer(value)
          } else {
            onAnswer(value)
          }
        }}
      >
        <TextField
          className="flex-1"
          label="Nuevo valor"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder={
            isCurrency
              ? formatCOP(Number(question.current_value) || 0)
              : String(question.current_value ?? '')
          }
          inputMode={isCurrency || isInteger ? 'numeric' : 'text'}
          disabled={disabled}
        />
        <Button type="submit" disabled={disabled || !value.trim()} className="min-h-12">
          Guardar
        </Button>
      </form>
    )
  }

  const options = question.type === 'enum' ? optionsForField(question.field) : []
  if (options.length > 0) {
    return (
      <div className="flex flex-wrap gap-2" role="group" aria-label="Opciones">
        {options.map((option) => (
          <Button
            key={option.value}
            disabled={disabled}
            variant="secondary"
            className="min-h-12 px-4"
            onClick={() => onAnswer(option.value)}
          >
            {option.label}
          </Button>
        ))}
      </div>
    )
  }

  return (
    <form
      className="flex flex-col gap-3 sm:flex-row"
      onSubmit={(event) => {
        event.preventDefault()
        if (value.trim()) onAnswer(value)
      }}
    >
      <TextField
        className="flex-1"
        aria-label="Tu respuesta"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder={
          question.type === 'currency'
            ? 'Ej. 2.500.000'
            : question.type === 'integer'
              ? 'Ej. 2'
              : 'Escribe tu respuesta'
        }
        inputMode={question.type === 'currency' || question.type === 'integer' ? 'numeric' : 'text'}
        disabled={disabled}
      />
      <Button type="submit" disabled={disabled || !value.trim()} className="min-h-12">
        Continuar
      </Button>
    </form>
  )
}
