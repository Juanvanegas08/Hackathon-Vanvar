import { useId } from 'react'

/**
 * Bubbles gooey en amarillo, con cobertura estable (sin vacíos blancos grandes).
 */
export const AmbientBackground = () => {
  const uid = useId().replace(/:/g, '')
  const filterId = `goo-${uid}`

  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
      <div className="gradient-bg">
        {/* Capa fija: siempre hay amarillo en la zona del hero */}
        <div className="bubble-base-glow" />

        <svg xmlns="http://www.w3.org/2000/svg" className="gradient-bg-svg">
          <defs>
            <filter id={filterId}>
              <feGaussianBlur in="SourceGraphic" stdDeviation="10" result="blur" />
              <feColorMatrix
                in="blur"
                mode="matrix"
                values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 18 -8"
                result="goo"
              />
              <feBlend in="SourceGraphic" in2="goo" />
            </filter>
          </defs>
        </svg>

        <div
          className="gradients-container"
          style={{ filter: `url(#${filterId}) blur(40px)` }}
        >
          <div className="g1" />
          <div className="g2" />
          <div className="g3" />
          <div className="g4" />
          <div className="g5" />
          <div className="g6" />
        </div>
      </div>
      <div className="gradient-bg-veil" />
    </div>
  )
}
