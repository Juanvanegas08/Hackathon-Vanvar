import { useEffect, useId, useRef } from 'react'

/**
 * Bubbles gooey muy dinámicas (amarillo CasaLista).
 */
export const AmbientBackground = () => {
  const uid = useId().replace(/:/g, '')
  const filterId = `goo-${uid}`
  const interactiveRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const reduceMotion =
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduceMotion) return

    const bubble = interactiveRef.current
    if (!bubble) return

    let curX = window.innerWidth * 0.65
    let curY = window.innerHeight * 0.35
    let tgX = curX
    let tgY = curY
    let raf = 0
    let running = true

    const move = () => {
      if (!running) return
      curX += (tgX - curX) / 12
      curY += (tgY - curY) / 12
      bubble.style.transform = `translate(${Math.round(curX)}px, ${Math.round(curY)}px)`
      raf = window.requestAnimationFrame(move)
    }

    const onMouseMove = (event: MouseEvent) => {
      tgX = event.clientX
      tgY = event.clientY
    }

    window.addEventListener('mousemove', onMouseMove)
    raf = window.requestAnimationFrame(move)

    return () => {
      running = false
      window.cancelAnimationFrame(raf)
      window.removeEventListener('mousemove', onMouseMove)
    }
  }, [])

  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
      <div className="gradient-bg">
        <div className="bubble-base-glow" />
        <div className="bubble-base-glow bubble-base-glow-b" />

        <svg xmlns="http://www.w3.org/2000/svg" className="gradient-bg-svg">
          <defs>
            <filter id={filterId}>
              <feGaussianBlur in="SourceGraphic" stdDeviation="12" result="blur" />
              <feColorMatrix
                in="blur"
                mode="matrix"
                values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 20 -9"
                result="goo"
              />
              <feBlend in="SourceGraphic" in2="goo" />
            </filter>
          </defs>
        </svg>

        <div
          className="gradients-container"
          style={{ filter: `url(#${filterId}) blur(36px)` }}
        >
          <div className="g1" />
          <div className="g2" />
          <div className="g3" />
          <div className="g4" />
          <div className="g5" />
          <div className="g6" />
          <div className="g7" />
          <div className="g8" />
          <div ref={interactiveRef} className="interactive" />
        </div>
      </div>
      <div className="gradient-bg-veil" />
    </div>
  )
}
