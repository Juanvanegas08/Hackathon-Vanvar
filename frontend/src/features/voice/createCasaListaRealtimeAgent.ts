import { tool, RealtimeAgent } from '@openai/agents/realtime'
import { z } from 'zod'
import {
  completeVoiceProfile,
  getVoiceContext,
  submitVoiceAnswer,
} from '@/api/voice.api'

const AGENT_INSTRUCTIONS = `
Eres CasaLista, un asesor virtual de vivienda.

Hablas en español colombiano neutral, de manera cálida, clara, respetuosa y breve.

Tu propósito es conversar con la persona para completar su perfil de vivienda y entregarle opciones compatibles.

Reglas obligatorias:

1. Haz únicamente una pregunta principal a la vez.
2. No conviertas la conversación en un interrogatorio.
3. Mantén respuestas cortas, generalmente de una o dos frases.
4. No inventes información.
5. No calcules por tu cuenta puntajes, capacidad crediticia, categorías o proyectos.
6. El backend de CasaLista es la única fuente de verdad.
7. Antes de comenzar, consulta la herramienta get_voice_context.
8. Utiliza exactamente la pregunta o intención indicada por el backend.
9. Después de cada respuesta del usuario, utiliza submit_current_answer.
10. No afirmes que guardaste información hasta que la herramienta confirme éxito.
11. Si la herramienta rechaza una respuesta, pide una aclaración breve.
12. No preguntes información que ya esté confirmada.
13. Si un dato está precargado, pide confirmación sin revelar cifras sensibles innecesariamente.
14. Confirma cuidadosamente ingresos, ahorros y obligaciones.
15. No prometas aprobación de crédito.
16. No digas que una persona tiene garantizada una vivienda.
17. No rechaces automáticamente a personas no afiliadas.
18. Para una persona no afiliada, explica únicamente cuando corresponda que la continuidad depende de la disponibilidad comercial destinada a no afiliados.
19. No menciones IDs, endpoints, JSON, herramientas ni detalles técnicos.
20. No reveles que la afiliación proviene de un servicio simulado.
21. Si el usuario pregunta algo fuera del flujo, responde brevemente y regresa a la pregunta pendiente.
22. Si el usuario no entiende, reformula la pregunta sin cambiar su intención.
23. Si la persona interrumpe, detente y escucha.
24. Cuando el backend indique que el perfil está completo, llama a complete_voice_profile.
25. Utiliza la frase de cierre entregada por la herramienta.
26. Después del cierre, no hagas más preguntas de perfilamiento.
27. Este resultado es orientativo y no constituye una aprobación de crédito.
`

export interface CasaListaAgentOptions {
  leadId: string
  displayName?: string | null
  voice?: string
  onProfileCompleted?: (navigationPath: string) => void
}

export const createCasaListaRealtimeAgent = (options: CasaListaAgentOptions) => {
  const { leadId, displayName, voice = 'marin', onProfileCompleted } = options

  const get_voice_context = tool({
    name: 'get_voice_context',
    description:
      'Obtiene el estado actual del perfil y la única pregunta que debe hacerse a continuación.',
    parameters: z.object({}),
    execute: async () => {
      const context = await getVoiceContext(leadId)
      return JSON.stringify({
        known_lead: context.known_lead,
        display_name: context.display_name,
        identity_status: context.identity_status,
        profile_completed: context.profile_completed,
        progress: context.progress,
        next_question: context.next_question
          ? {
              field: context.next_question.field,
              question: context.next_question.question,
              type: context.next_question.type,
              confirmation_required: context.next_question.confirmation_required,
            }
          : null,
        conversation_opening: context.conversation_opening,
        fields_to_confirm: context.fields_to_confirm,
        warnings: context.warnings,
        demo_mode: context.demo_mode,
      })
    },
  })

  const submit_current_answer = tool({
    name: 'submit_current_answer',
    description:
      'Envía la respuesta del usuario a la pregunta actual. Solo debe utilizarse después de escuchar una respuesta relacionada con la pregunta activa.',
    parameters: z.object({
      field: z.string(),
      rawTranscript: z.string(),
      normalizedValue: z.union([z.string(), z.number(), z.boolean(), z.null()]),
      action: z.enum(['answer', 'confirm', 'correct', 'skip']),
    }),
    execute: async ({ field, rawTranscript, normalizedValue, action }) => {
      const result = await submitVoiceAnswer(leadId, {
        field,
        raw_transcript: rawTranscript,
        normalized_value: normalizedValue,
        action,
      })
      return JSON.stringify(result)
    },
  })

  const complete_voice_profile = tool({
    name: 'complete_voice_profile',
    description:
      'Finaliza el perfilamiento cuando el backend ya no tiene preguntas prioritarias y prepara los resultados.',
    parameters: z.object({}),
    execute: async () => {
      const result = await completeVoiceProfile(leadId)
      if (result.completed) {
        onProfileCompleted?.(result.navigation_path)
      }
      return JSON.stringify({
        completed: result.completed,
        assistant_closing: result.assistant_closing,
        spoken_summary: result.spoken_summary,
        navigation_path: result.navigation_path,
        recommendations_count: result.recommendations_count,
        top_project: result.top_project,
        recommended_projects: result.recommended_projects,
        disclaimer: result.disclaimer,
      })
    },
  })

  return new RealtimeAgent({
    name: 'CasaLista',
    voice,
    instructions: [
      AGENT_INSTRUCTIONS,
      displayName ? `El nombre visible del usuario es ${displayName}.` : '',
      'Al iniciar, llama get_voice_context antes de saludar.',
      'Cuando complete_voice_profile responda, di en voz alta assistant_closing o spoken_summary: nombra el proyecto, di por qué y menciona el link del brochure si existe.',
    ]
      .filter(Boolean)
      .join('\n'),
    tools: [get_voice_context, submit_current_answer, complete_voice_profile],
  })
}
