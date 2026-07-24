import { AnimatePresence, motion } from 'framer-motion'
import { ChevronLeft, ChevronRight, ExternalLink, FileText, MapPin } from 'lucide-react'
import { useEffect, useState } from 'react'
import { BROCHURES } from '@/data/brochures'
import { Button } from '@/components/ui/Button'

export const BrochureShowcase = () => {
  const [index, setIndex] = useState(0)
  const total = BROCHURES.length
  const current = BROCHURES[index]

  useEffect(() => {
    const timer = window.setInterval(() => {
      setIndex((prev) => (prev + 1) % total)
    }, 7000)
    return () => window.clearInterval(timer)
  }, [total, index])

  const goPrev = () => setIndex((prev) => (prev - 1 + total) % total)
  const goNext = () => setIndex((prev) => (prev + 1) % total)

  if (!current) return null

  return (
    <section className="border-t border-[var(--color-line)] py-8 text-left sm:py-10">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3 sm:mb-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-green)]">
            Brochures de proyectos
          </p>
          <h2 className="mt-2 font-display text-3xl text-[var(--color-ink)] sm:text-4xl">
            Conoce las opciones, una a una
          </h2>
        </div>
        <p className="text-sm text-[var(--color-muted)]">
          {index + 1} / {total}
        </p>
      </div>

      <div className="overflow-hidden rounded-[2rem] border border-[var(--color-line)] bg-white">
        <AnimatePresence mode="wait">
          <motion.div
            key={current.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3 }}
            className="grid items-stretch lg:grid-cols-[minmax(0,1fr)_minmax(280px,420px)]"
          >
            <div className="flex flex-col justify-center p-6 sm:p-10 lg:p-12">
              <p className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--color-muted)]">
                <MapPin size={15} aria-hidden />
                {current.ubicacion}
              </p>
              <h3 className="mt-3 font-display text-4xl tracking-tight text-[var(--color-ink)] sm:text-5xl">
                {current.proyecto}
              </h3>
              <p className="mt-4 max-w-md text-[var(--color-muted)]">
                Mira la portada del proyecto y abre el brochure digital para explorar planos y
                tipologías.
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-3">
                <a href={current.url} target="_blank" rel="noreferrer">
                  <Button className="min-h-12 gap-2 px-6">
                    <FileText size={17} aria-hidden />
                    Ver brochure
                    <ExternalLink size={15} aria-hidden />
                  </Button>
                </a>
                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    className="min-h-12 w-12 px-0"
                    aria-label="Brochure anterior"
                    onClick={goPrev}
                  >
                    <ChevronLeft size={20} />
                  </Button>
                  <Button
                    variant="secondary"
                    className="min-h-12 w-12 px-0"
                    aria-label="Siguiente brochure"
                    onClick={goNext}
                  >
                    <ChevronRight size={20} />
                  </Button>
                </div>
              </div>

              <div className="mt-10 flex flex-wrap gap-1.5">
                {BROCHURES.map((item, dotIndex) => (
                  <button
                    key={item.id}
                    type="button"
                    aria-label={`Ir a ${item.proyecto}`}
                    onClick={() => setIndex(dotIndex)}
                    className={
                      dotIndex === index
                        ? 'h-2 w-6 rounded-full bg-[var(--color-blue)]'
                        : 'h-2 w-2 rounded-full bg-[var(--color-line)] hover:bg-[var(--color-muted)]'
                    }
                  />
                ))}
              </div>
            </div>

            <a
              href={current.url}
              target="_blank"
              rel="noreferrer"
              className="group relative block min-h-[340px] bg-[#eef2f6] lg:min-h-full"
              aria-label={`Abrir brochure de ${current.proyecto}`}
            >
              <div className="absolute inset-0 flex items-center justify-center p-6 sm:p-8">
                <motion.img
                  key={current.coverImage}
                  src={current.coverImage}
                  alt={`Portada del brochure ${current.proyecto}`}
                  initial={{ opacity: 0.4, scale: 0.98 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.35 }}
                  className="h-full max-h-[420px] w-auto max-w-full rounded-md object-contain shadow-[0_18px_40px_rgba(18,20,26,0.16)] transition duration-300 group-hover:-translate-y-0.5 group-hover:shadow-[0_22px_48px_rgba(18,20,26,0.2)]"
                  loading="eager"
                  decoding="async"
                />
              </div>
              <div className="pointer-events-none absolute inset-x-0 bottom-0 h-1 bg-black/5">
                <motion.div
                  key={`progress-${current.id}`}
                  className="h-full bg-[var(--color-blue)]/70"
                  initial={{ width: '0%' }}
                  animate={{ width: '100%' }}
                  transition={{ duration: 7, ease: 'linear' }}
                />
              </div>
            </a>
          </motion.div>
        </AnimatePresence>
      </div>
    </section>
  )
}
