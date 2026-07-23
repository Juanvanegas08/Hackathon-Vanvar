import type { InputHTMLAttributes } from 'react'
import { cn } from '@/utils/cn'

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> { label?: string; error?: string }
export const TextField = ({ label, error, className, id, ...props }: TextFieldProps) => (
  <label className="block space-y-1.5 text-left text-sm font-medium text-[var(--color-ink)]" htmlFor={id}>
    {label && <span>{label}</span>}
    <input id={id} className={cn('w-full rounded-2xl border border-[var(--color-line)] bg-white px-4 py-3 text-base outline-none transition focus:border-[var(--color-blue)] focus:ring-2 focus:ring-[var(--color-blue)]/15', error && 'border-red-500', className)} {...props} />
    {error && <span className="text-sm text-red-600">{error}</span>}
  </label>
)
