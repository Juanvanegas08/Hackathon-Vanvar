import { tool, RealtimeAgent } from '@openai/agents/realtime'
import { z } from 'zod'
import {
  completeVoiceProfile,
  getVoiceContext,
  reportVoiceEngagement,
  submitVoiceAnswer,
} from '@/api/voice.api'

// Canonical copy also lives in backend/app/services/laura_agent_instructions.py
// (phone Realtime). Keep both in sync — do not diverge pacing/style for phone.
const AGENT_INSTRUCTIONS = `
Eres Laura, asesora virtual de Colsubsidio para orientación de vivienda (plataforma CasaLista).
Eres mujer, hablas con voz femenina y te presentas siempre como Laura.

Quién eres:
- Asesora de Colsubsidio: cálida, clara, colombiana. Acompañas a decidir vivienda.
- NO eres un formulario hablado. NO suenes a encuesta ni a call center.

IDIOMA:
- Solo español colombiano. Si el audio parece otro idioma o raro, pide que repita en español.

Ritmo (prioridad: corto y rápido):
- Habla como en una llamada real: natural y MUY breve.
- Al avanzar el perfil: UNA sola frase corta (ideal ≤12 palabras). Nada más.
- Tras una respuesta clara: ve DIRECTO a la siguiente pregunta. Cero preámbulo.
- Reformula SIEMPRE la pregunta del backend en lenguaje sencillo. Nunca la leas literal ni con jerga ("reportado por empleador", "obligaciones financieras", "perfilamiento").
- Ejemplos de reformulación (varía; no copies siempre la misma):
  · salario → "¿Cuánto ganas al mes?" / "¿Más o menos cuánto te entra al mes?"
  · ingreso hogar → "¿Cuánto entra en la casa entre todos?"
  · ahorro → "¿Cuánto tienes ahorrado para vivienda?"
  · deudas → "¿Cuánto pagas al mes en cuotas?"
  · personas a cargo → "¿Cuántas personas tienes a cargo?"
  · proyecto → "¿Tienes algún proyecto en mente, o prefieres que yo te oriente?"
- Una sola pregunta por turno (salvo el arranque). Espera la respuesta.
- Si la persona duda: un ejemplo corto en la misma frase.
- Si aclara una duda del usuario: máximo 1–2 frases, luego retoma.

Arranque humano (excepción, solo al inicio):
- 2–3 frases: saludo + marco ("unas preguntas sencillas, tipo dos o tres minutos") + si lo hacen ahora o más tarde.
- Si opening_hint/conversation_opening ya trae ese marco, úsalo reformulado; no suenes a formulario.
- Si dicen que prefieren más tarde: despídete cálida en una frase y no sigas preguntando.
- Si aceptan ahora: submit_current_answer de consentimiento=true y sigue.

PROHIBIDO — muletillas, meta-habla y menús (CRÍTICO):
- No uses: "perfecto", "excelente", "súper", "muy bien", "claro", "ah ok", "ok", "listo", "vale", "entiendo", "tiene sentido", "genial", "buenísimo", "de una", "dale", "ajá".
- No digas "gracias" (máximo 1 vez, solo al cierre si hace falta).
- NUNCA digas que vas a "reportar", "guardar", "enviar", "registrar" o "pasar" un dato. El usuario no debe oír el proceso interno.
- NUNCA digas "ya te hago la siguiente pregunta", "déjame anotar", "un segundo mientras…".
- NUNCA digas "espérame", "voy a analizar", "déjame revisar", "un momento", "estoy procesando".
- No parafrasees lo que la persona acaba de decir.
- Si algo sale mal o no entendiste: repregunta SIMPLE al instante. No ofrezcas menús tipo "¿continuar, editar, corregir o cancelar?".
- No digas "un segundo", "a ver", "déjame ver", "como te decía".
- Si el tool tarda: quédate en silencio hasta tener el resultado; luego habla. No rellenes con espera.

Velocidad de respuesta:
- Prioriza hablar YA. Primero submit_current_answer; en cuanto accepted=true, di solo la siguiente pregunta corta.
- NO llames report_user_engagement ni get_voice_context entre turnos normales.
- No inventes frases de relleno mientras "piensas".

Interrupciones y correcciones (CRÍTICO):
- Si te interrumpen: DETENTE al instante. Responde SOLO a lo último que dijo, corto.
- Si dice "perdón" / "mejor…" / corrige a mitad: ignora el fragmento viejo; usa la última intención.
- No te quedes en disculpas ni digas "como te decía". Retoma limpio.
- En proyecto_interes: "no", "ninguno", "lo que me recomiendes", "tú decides" = respuesta válida (sin preferencia). Haz submit_current_answer YA (action=skip o normalizedValue="sin preferencia") y cierra el perfil si corresponde. No repregúntes ni te trabes.

Clasificación de cada turno (antes de hablar o guardar):
A) RESPUESTA usable → submit_current_answer (answersCurrentQuestion=true, userIntent="answer").
B) PREGUNTA/DUDA → NO guardes. Contesta en 1–2 frases y retoma.
C) RUIDO/FILLER → no guardes; repregunta breve.
D) AMBIGUA → confirma en media frase. No guardes hasta aclarar.

Señales de PREGUNTA: duda clara ("qué significa", "tengo una duda", "explícame")…
Señales de RESPUESTA: dato directo (sí/no, número, lugar, plazo), "lo que me recomiendes", o confirmación/corrección.

Reglas operativas:
1. Una pregunta principal a la vez.
2. No interrogatorio ni tono de formulario.
3. No inventes proyectos, cupos, tasas ni aprobaciones.
4. No calcules puntajes ni categorías por tu cuenta.
5. El backend es la única fuente de verdad.
6. Al inicio: saludo humano + marco 2–3 min + si ahora o más tarde (usa opening_hint si viene). SIN tools primero si ya tienes contexto.
7. Tras submit_current_answer accepted=true: usa next_question del resultado. NO get_voice_context.
8. report_user_engagement: casi nunca. Solo 1 vez al cierre o si el tono cambia de forma extrema.
9. submit_current_answer SOLO si es RESPUESTA real. Enums: situacion_crediticia (sin_reportes, al_dia, atrasos_menores, atrasos_mayores, en_proceso_normalizacion, desconocida); plazo_compra (inmediato, 3_meses, 6_meses, 12_meses, mas_de_un_ano, no_definido). proyecto_interes opcional: "lo que me recomiendes"/skip → normalizedValue="sin preferencia".
10. No afirmes que guardaste hasta accepted=true (y ni así lo digas en voz).
11. Si rechazan por duda: responde corto; luego retoma. Si inválida: repregunta en una frase. Sin menús.
12. No repitas datos ya confirmados.
13. Confirma ingresos/ahorros/obligaciones con pregunta corta.
14. No prometas aprobación de crédito ni vivienda garantizada.
15. No rechaces automáticamente a no afiliados.
16. No menciones IDs, JSON, tools ni detalles técnicos.
17. Si pregunta, contéstale breve antes de seguir el perfil.
18. Si no entiende, reformúlala más corta con un ejemplo distinto.
19. Perfil completo → complete_voice_profile y LEE SOLO assistant_closing/spoken_summary. No inventes opciones extra ni menús al final.
20. Después del cierre, no más preguntas de perfil.
21. Preséntate como Laura (Colsubsidio). CasaLista es la plataforma, no tu nombre.
22. Si complete_voice_profile falla: silencio o "ya casi"; reintenta UNA vez.
`

export interface CasaListaAgentOptions {
  leadId: string
  displayName?: string | null
  voice?: string
  onProfileCompleted?: (navigationPath: string) => void
  /** Prefetched voice context so the first turn skips a tool round-trip. */
  initialContextSummary?: string | null
}

export const createCasaListaRealtimeAgent = (options: CasaListaAgentOptions) => {
  const {
    leadId,
    displayName,
    voice = 'coral',
    onProfileCompleted,
    initialContextSummary,
  } = options

  const get_voice_context = tool({
    name: 'get_voice_context',
    description:
      'Obtiene el estado actual del perfil y la siguiente pregunta. ' +
      'Úsala solo al inicio si no trajiste contexto, o si perdiste el hilo. ' +
      'NO la llames tras cada submit_current_answer si el resultado ya trae next_question.',
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

  const looksLikeUserQuestion = (transcript: string) => {
    const text = transcript.trim().toLowerCase()
    if (!text) return false
    if (text.includes('?') || text.includes('¿')) return true
    const doubtPhrases = [
      'una duda',
      'tengo una duda',
      'una pregunta',
      'tengo una pregunta',
      'qué significa',
      'que significa',
      'no entend',
      'no te entend',
      'puedes repetir',
      'puedes explicar',
      'me puedes explicar',
      'quiero saber',
      'quisiera saber',
      'qué quieres decir',
      'que quieres decir',
      'me recomiendas algo',
      'qué me recomiendas',
      'que me recomiendas',
      'hay forma de',
      'cómo funciona',
      'como funciona',
      'qué es eso',
      'que es eso',
      'explica un poco',
    ]
    if (doubtPhrases.some((phrase) => text.includes(phrase))) return true
    // Solo al inicio; si trae monto/número/sí-no, es respuesta (no duda).
    if (
      /^(qué|que|cómo|como|cuánto|cuanto|dónde|donde|cuál|cual|por\s*qué|por\s*que)\b/.test(
        text,
      )
    ) {
      if (/\d|mill[oó]n|mil\b|pesos|s[ií]\b|\bno\b|aprox|alrededor/.test(text)) {
        return false
      }
      return true
    }
    return false
  }

  const looksLikeNonAnswer = (transcript: string) => {
    const text = transcript.trim().toLowerCase()
    if (!text || text.length < 1) return true
    const fillers = [
      'eh',
      'ehh',
      'mmm',
      'este',
      'este...',
      'hola',
      'ok',
      'okay',
      'ajá',
      'aja',
      'ya',
      'bueno',
      'no sé',
      'no se',
      'nada',
      'lo que sea',
      'dale',
      'sigue',
    ]
    if (fillers.includes(text)) return true
    // Pure filler without content
    if (/^(eh+|mm+|ah+|uhm+|este\.?)+$/i.test(text)) return true
    return false
  }

  const rejectGuidance = (
    reason: string,
    kind: 'question' | 'non_answer' | 'invalid' = 'invalid',
  ) => {
    const assistant_guidance =
      kind === 'question'
        ? `${reason} NO guardes nada. Contesta en 1–2 frases cortas y retoma la pregunta activa. Sin muletillas.`
        : kind === 'non_answer'
          ? `${reason} NO guardes nada. Repregunta el dato en una sola frase corta. Sin menús.`
          : `${reason} NO guardes nada. Repregunta el campo activo en una frase. Sin menús continuar/editar.`
    return JSON.stringify({
      accepted: false,
      clarification_required: true,
      user_turn_kind: kind,
      assistant_guidance,
      validation_message: reason,
    })
  }

  const submit_current_answer = tool({
    name: 'submit_current_answer',
    description:
      'Guarda un dato del perfil SOLO cuando el usuario realmente RESPONDE la pregunta activa. ' +
      'Antes de llamar, clasifica el turno con userIntent. ' +
      'Si el usuario pregunta o tiene una duda: userIntent="question", answersCurrentQuestion=false (o no llames la tool) y CONTÉSTALE en voz. ' +
      'Nunca trates una pregunta como si fuera el valor del campo.',
    parameters: z.object({
      field: z.string(),
      rawTranscript: z.string(),
      normalizedValue: z.union([z.string(), z.number(), z.boolean(), z.null()]),
      action: z.enum(['answer', 'confirm', 'correct', 'skip']),
      answersCurrentQuestion: z.boolean(),
      userIntent: z.enum([
        'answer',
        'question',
        'unclear',
        'off_topic',
        'filler',
      ]),
    }),
    execute: async ({
      field,
      rawTranscript,
      normalizedValue,
      action,
      answersCurrentQuestion,
      userIntent,
    }) => {
      const deferProject =
        field === 'proyecto_interes' &&
        (action === 'skip' ||
          /lo que me recomiend|sin preferencia|no tengo|ningun|t[uú] decides|como veas|da igual|no s[eé]/i.test(
            rawTranscript || '',
          ))

      let effectiveAction = action
      let effectiveValue = normalizedValue
      let effectiveIntent = userIntent
      let effectiveAnswers = answersCurrentQuestion

      if (deferProject) {
        effectiveAction = 'answer'
        effectiveValue = 'sin preferencia'
        effectiveIntent = 'answer'
        effectiveAnswers = true
      }

      if (
        !deferProject &&
        (effectiveIntent === 'question' || looksLikeUserQuestion(rawTranscript))
      ) {
        return rejectGuidance(
          'El usuario está preguntando o pidiendo aclaración, no respondiendo el campo.',
          'question',
        )
      }
      if (
        !deferProject &&
        (!effectiveAnswers ||
          effectiveIntent === 'unclear' ||
          effectiveIntent === 'off_topic' ||
          effectiveIntent === 'filler')
      ) {
        return rejectGuidance(
          'El turno no es una respuesta usable a la pregunta activa.',
          effectiveIntent === 'filler' || effectiveIntent === 'off_topic'
            ? 'non_answer'
            : 'invalid',
        )
      }
      if (!deferProject && looksLikeNonAnswer(rawTranscript)) {
        return rejectGuidance(
          'El audio/transcript no contiene una respuesta usable al campo.',
          'non_answer',
        )
      }
      if (
        effectiveAction === 'answer' &&
        (effectiveValue === null ||
          effectiveValue === undefined ||
          (typeof effectiveValue === 'string' && !effectiveValue.trim()))
      ) {
        return rejectGuidance(
          'No hay normalizedValue usable para la pregunta activa.',
          'invalid',
        )
      }

      const result = await submitVoiceAnswer(leadId, {
        field,
        raw_transcript: rawTranscript,
        normalized_value: effectiveValue,
        action: effectiveAction,
      })
      window.dispatchEvent(
        new CustomEvent('casalista-lead-updated', { detail: { leadId } }),
      )
      if (!result.accepted || result.clarification_required) {
        const looksQuestion = looksLikeUserQuestion(rawTranscript)
        return JSON.stringify({
          accepted: false,
          clarification_required: true,
          field: result.next_question?.field ?? field,
          next_question: result.next_question
            ? {
                field: result.next_question.field,
                question: result.next_question.question,
                type: result.next_question.type,
              }
            : null,
          user_turn_kind: looksQuestion ? 'question' : 'invalid',
          assistant_guidance: looksQuestion
            ? 'Contesta en 1–2 frases y retoma la pregunta activa. Sin esperas ni menús.'
            : 'Repregunta el mismo campo en una frase corta. Sin "un segundo" ni menús.',
        })
      }
      return JSON.stringify({
        accepted: true,
        updated_field: result.updated_field,
        profile_completed: result.profile_completed,
        progress: result.progress,
        next_question: result.next_question
          ? {
              field: result.next_question.field,
              question: result.next_question.question,
              type: result.next_question.type,
            }
          : null,
        speak_now:
          result.profile_completed
            ? 'Llama complete_voice_profile ya. No digas que vas a analizar.'
            : 'Di SOLO la siguiente pregunta (≤12 palabras). Sin muletillas, eco ni "un segundo".',
      })
    },
  })

  const report_user_engagement = tool({
    name: 'report_user_engagement',
    description:
      'Registra predisposición del usuario. Úsala casi nunca: solo 1 vez al cierre. NUNCA entre turnos (añade latencia).',
    parameters: z.object({
      label: z.enum([
        'interesado',
        'indeciso',
        'molesto',
        'trolleando',
        'ocupado',
        'desconocido',
      ]),
      score: z.number().min(0).max(100).nullable(),
      reason: z.string().nullable(),
    }),
    execute: async ({ label, score, reason }) => {
      // No bloquear el turno de voz: fire-and-forget.
      void reportVoiceEngagement(leadId, {
        label,
        score,
        reason,
      })
        .then((result) => {
          window.dispatchEvent(
            new CustomEvent('casalista-engagement-updated', { detail: result }),
          )
        })
        .catch(() => undefined)
      return JSON.stringify({ ok: true, deferred: true })
    },
  })

  const complete_voice_profile = tool({
    name: 'complete_voice_profile',
    description:
      'Finaliza el perfilamiento cuando next_question sea null / profile_completed=true. Puede tardar. Quédate en silencio hasta el resultado; no digas "un segundo".',
    parameters: z.object({}),
    execute: async () => {
      try {
        const result = await completeVoiceProfile(leadId)
        if (result.completed) {
          window.setTimeout(() => {
            onProfileCompleted?.(result.navigation_path)
          }, 80)
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
          speak_now:
            'LEE EN VOZ ALTA SOLO el assistant_closing o spoken_summary. ' +
            'No inventes menús (continuar/editar/cancelar). No agregues preguntas nuevas.',
        })
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : 'No se pudo completar el cierre ahora.'
        return JSON.stringify({
          completed: false,
          error: true,
          retryable: true,
          message,
          assistant_guidance:
            'Silencio o "ya casi". Reintenta complete_voice_profile UNA vez. No digas error ni "estoy analizando".',
        })
      }
    },
  })

  return new RealtimeAgent({
    name: 'Laura',
    voice,
    instructions: [
      AGENT_INSTRUCTIONS,
      displayName ? `El nombre visible del usuario es ${displayName}.` : '',
      initialContextSummary
        ? `Contexto inicial ya cargado (úsalo al saludar; no llames get_voice_context primero):\n${initialContextSummary}`
        : 'Al iniciar, si no tienes contexto, llama get_voice_context una vez antes de saludar.',
      'Corto y sencillo: tras cada respuesta, solo la siguiente pregunta (≤12 palabras). Sin meta-habla ni menús.',
      'Tras submit_current_answer accepted=true, di solo next_question al instante. Sin tools extras.',
      'Cuando complete_voice_profile responda completed=true: LEE SOLO assistant_closing/spoken_summary. Sin inventar opciones.',
    ]
      .filter(Boolean)
      .join('\n'),
    tools: [
      get_voice_context,
      submit_current_answer,
      report_user_engagement,
      complete_voice_profile,
    ],
  })
}
