import { X } from 'lucide-react'
import type { PropsWithChildren } from 'react'
import { Button } from '@/components/ui/Button'

interface ModalProps extends PropsWithChildren { open: boolean; title: string; onClose: () => void }
export const Modal = ({ open, title, onClose, children }: ModalProps) => !open ? null : (
  <div className="fixed inset-0 z-50 grid place-items-center bg-black/35 p-4" role="presentation" onMouseDown={onClose}>
    <section className="w-full max-w-lg rounded-3xl bg-white p-6 surface-shadow" role="dialog" aria-modal="true" aria-labelledby="modal-title" onMouseDown={(event) => event.stopPropagation()}>
      <header className="mb-5 flex items-center justify-between gap-4"><h2 id="modal-title" className="font-display text-2xl">{title}</h2><Button variant="ghost" className="min-h-0 px-2 py-2" aria-label="Cerrar" onClick={onClose}><X size={20} /></Button></header>
      {children}
    </section>
  </div>
)
