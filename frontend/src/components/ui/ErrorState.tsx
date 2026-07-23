import { AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/Button'
interface ErrorStateProps { message: string; onRetry?: () => void }
export const ErrorState = ({ message, onRetry }: ErrorStateProps) => <div className="rounded-3xl border border-red-200 bg-red-50 p-6 text-center"><AlertCircle className="mx-auto mb-3 text-red-600" /><p className="text-[var(--color-ink)]">{message}</p>{onRetry && <Button variant="secondary" className="mt-4" onClick={onRetry}>Intentar de nuevo</Button>}</div>
