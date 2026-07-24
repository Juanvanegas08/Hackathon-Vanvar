/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_DEMO_MODE: string
  readonly VITE_VOICE_PROVIDER: string
  readonly VITE_VOICE_ENABLED: string
  readonly VITE_ADVISOR_MOCK: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
