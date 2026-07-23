import type { ButtonHTMLAttributes } from 'react'
import { cn } from '@/utils/cn'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> { variant?: ButtonVariant }
const styles: Record<ButtonVariant, string> = {
  primary: 'bg-[var(--color-yellow)] text-[var(--color-ink)] hover:bg-[var(--color-yellow-soft)]',
  secondary: 'bg-[#f1f0eb] text-[var(--color-ink)] hover:bg-[#e8e6df]',
  ghost: 'bg-transparent text-[var(--color-blue)] hover:bg-white',
  danger: 'bg-red-600 text-white hover:bg-red-700',
}
export const Button = ({ className, variant = 'primary', type = 'button', ...props }: ButtonProps) => (
  <button type={type} className={cn('inline-flex min-h-11 items-center justify-center rounded-full px-5 py-2.5 font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50', styles[variant], className)} {...props} />
)
