const pickSpanishVoice = (): SpeechSynthesisVoice | null => {
  if (typeof window === 'undefined' || !window.speechSynthesis) return null
  const voices = window.speechSynthesis.getVoices()
  const preferred = voices.find(
    (voice) =>
      /es[-_]CO/i.test(voice.lang) ||
      (/es/i.test(voice.lang) && /female|mujer|sabina|paulina|lucia|monica|elena/i.test(voice.name)),
  )
  if (preferred) return preferred
  return voices.find((voice) => voice.lang.toLowerCase().startsWith('es')) ?? null
}

export const buildLauraRecommendationScript = (spokenSummary: string): string => {
  const text = spokenSummary.trim()
  if (!text) return ''
  if (/^según la charla/i.test(text)) return text
  return (
    `Según la charla que tuve contigo, y después de revisar los proyectos del catálogo, ` +
    `${text.charAt(0).toLowerCase()}${text.slice(1)}`
  )
}

export const speakLauraText = (
  text: string,
  options?: { onStart?: () => void; onEnd?: () => void; onError?: () => void },
): (() => void) => {
  if (typeof window === 'undefined' || !window.speechSynthesis || !text.trim()) {
    options?.onError?.()
    return () => undefined
  }

  window.speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = 'es-CO'
  utterance.rate = 1
  utterance.pitch = 1.05
  const voice = pickSpanishVoice()
  if (voice) utterance.voice = voice

  utterance.onstart = () => options?.onStart?.()
  utterance.onend = () => options?.onEnd?.()
  utterance.onerror = () => options?.onError?.()

  // Algunas veces las voces llegan async; reintentar tras voiceschanged.
  const speak = () => window.speechSynthesis.speak(utterance)
  if (window.speechSynthesis.getVoices().length === 0) {
    const onVoices = () => {
      const lateVoice = pickSpanishVoice()
      if (lateVoice) utterance.voice = lateVoice
      window.speechSynthesis.removeEventListener('voiceschanged', onVoices)
      speak()
    }
    window.speechSynthesis.addEventListener('voiceschanged', onVoices)
    window.setTimeout(speak, 250)
  } else {
    speak()
  }

  return () => {
    window.speechSynthesis.cancel()
  }
}

export const stopLauraSpeech = () => {
  if (typeof window !== 'undefined' && window.speechSynthesis) {
    window.speechSynthesis.cancel()
  }
}
