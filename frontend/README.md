# CasaLista Voice — Frontend

Experiencia conversacional visual para perfilar leads de vivienda. Conecta con el backend FastAPI existente en `backend/`.

## Objetivo

Ofrecer una interfaz **voice-first** (simulada por texto en esta fase), moderna y sin formularios largos, para demostrar:

- Identificación simulada de afiliados
- Precarga y confirmación de datos
- Conversación de una pregunta a la vez
- Resultados orientativos y recomendaciones canónicas
- Vista comercial para asesores

## Tecnologías

- React 19 + Vite + TypeScript
- Tailwind CSS v4
- React Router
- TanStack Query
- Axios
- Framer Motion
- Lucide React
- Vitest + React Testing Library

## Instalación

```bash
cd frontend
npm install
cp .env.example .env
```

## Variables de entorno

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_DEMO_MODE=true
VITE_VOICE_PROVIDER=mock
VITE_VOICE_ENABLED=true
```

- `VITE_VOICE_PROVIDER=mock` — conversación por texto/botones (siempre disponible).
- `VITE_VOICE_PROVIDER=openai` — OpenAI Realtime vía WebRTC (requiere backend con `OPENAI_API_KEY`).
- Nunca coloques una API key de OpenAI en variables `VITE_*`.

## Voz real (OpenAI Realtime)

1. Configura en `backend/.env`:

```env
OPENAI_API_KEY=sk-...
OPENAI_REALTIME_ENABLED=true
OPENAI_REALTIME_MODEL=gpt-realtime-2.1
OPENAI_REALTIME_VOICE=marin
```

2. En `frontend/.env`:

```env
VITE_VOICE_PROVIDER=openai
VITE_VOICE_ENABLED=true
```

3. Flujo:
   - El navegador pide un **token efímero** a `POST /api/v1/realtime/client-secret`.
   - La clave real nunca sale del servidor.
   - El agente usa herramientas `get_voice_context`, `submit_current_answer` y `complete_voice_profile`.
   - Si la voz falla, la UI ofrece continuar por texto.
   - El provider mock se mantiene intacto.

### Privacidad

- No se guarda audio.
- No se persisten transcripciones.
- El micrófono solo se activa tras un clic explícito.
- Al salir se detienen tracks y se cierra la sesión.

### Limitaciones

- Costos variables por uso de OpenAI.
- Requiere micrófono y navegador con WebRTC.
- Todavía no hay Twilio ni llamadas telefónicas.
- El resultado sigue siendo orientativo (no es aprobación de crédito).

## Tecnologías

- React 18 + Vite + TypeScript
- Tailwind CSS
- React Router
- TanStack Query
- Axios
- Framer Motion
- Lucide React
- `@openai/agents` (Realtime + WebRTC)
- Zod
- Vitest + React Testing Library

## Backend requerido

En otra terminal:

```bash
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --reload
```

CORS ya permite `http://localhost:5173`.

## Ejecución

```bash
cd frontend
npm run dev
```

Abre [http://localhost:5173](http://localhost:5173).

## Flujos

### Afiliado conocido (`1000000001`)

1. Identificación → lookup `known_affiliate`
2. Consentimiento → `from-identity` con precarga
3. Confirmaciones (salario / personas a cargo)
4. Preguntas restantes
5. Resultados y recomendaciones

### No afiliado conocido (`1000000005`)

Mismo flujo; no se descarta. En resultados aparece contexto amable del 10%.

### Lead nuevo (`9999999999`)

Sin precarga; conversación completa desde cero.

## Modo demo

Ruta `/demo` para el jurado. Usa el mismo flujo real.

## Rutas

| Ruta | Descripción |
|------|-------------|
| `/` | Landing |
| `/identification` | Documento mínimo |
| `/consent` | Autorización / precarga |
| `/conversation/:leadId` | Experiencia conversacional |
| `/results/:leadId` | Resultados y proyectos |
| `/advisor` | Dashboard comercial |
| `/demo` | Escenarios del jurado |

## Arquitectura

- `src/api` — cliente HTTP tipado contra OpenAPI real
- `src/providers/VoiceSessionProvider` — mock de sesión de voz
- `src/store/flowStore` — estado mínimo del flujo
- `src/pages` — pantallas
- `src/components` — UI, conversación, recomendaciones

### Sustitución futura del mock de voz

Reemplazar `VoiceSessionProvider` por un `OpenAIRealtimeVoiceSessionProvider` que implemente la misma interfaz (`startSession`, `submitTextResponse`, `setVoiceState`, etc.) sin cambiar las páginas.

## Calidad

```bash
npm run lint
npm run typecheck
npm run test
npm run build
```

## Limitaciones

- La voz es simulada (texto + botones)
- Sin OpenAI Realtime, Twilio, OTP ni CRM
- Los leads viven en memoria del backend
- Los perfiles demo son completamente ficticios
- No aprueba créditos ni calcula capacidad oficial

## Identidad visual

Paleta temporal: amarillo cálido (acento), azul profundo (confianza), verde suave (progreso), fondos claros. Tipografía: **Fraunces** (display) + **Outfit** (UI). Variables CSS en `src/index.css` para sustituir cuando exista manual de marca.
