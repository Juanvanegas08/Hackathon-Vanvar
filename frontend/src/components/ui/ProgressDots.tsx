import { cn } from '@/utils/cn'
export const ProgressDots = ({ total, current }: { total: number; current: number }) => <div className="flex items-center gap-2" aria-label={`Paso ${current} de ${total}`}>{Array.from({ length: total }, (_, index) => <span key={index} className={cn('h-2 w-2 rounded-full bg-[var(--color-line)]', index < current && 'bg-[var(--color-green)]')} />)}</div>
