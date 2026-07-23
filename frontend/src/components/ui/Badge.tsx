import type { PropsWithChildren } from 'react'
import { cn } from '@/utils/cn'
export const Badge = ({ children, className }: PropsWithChildren<{ className?: string }>) => <span className={cn('inline-flex rounded-full bg-[var(--color-blue)] px-3 py-1 text-xs font-semibold text-white', className)}>{children}</span>
