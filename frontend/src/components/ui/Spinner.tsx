import { LoaderCircle } from 'lucide-react'
export const Spinner = ({ label = 'Cargando' }: { label?: string }) => <span className="inline-flex items-center gap-2 text-sm text-[var(--color-muted)]"><LoaderCircle className="animate-spin" size={18} aria-hidden="true" />{label}</span>
