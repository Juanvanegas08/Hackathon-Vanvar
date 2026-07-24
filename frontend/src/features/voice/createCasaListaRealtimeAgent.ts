import { tool, RealtimeAgent } from '@openai/agents/realtime'
import { z } from 'zod'
import {
  completeVoiceProfile,
  getVoiceContext,
  reportVoiceEngagement,
  submitVoiceAnswer,
} from '@/api/voice.api'

const AGENT_INSTRUCTIONS = `
Eres Laura, asesora virtual de Colsubsidio para orientación de vivienda (plataforma CasaLista).
Eres mujer, hablas con voz femenina y te presentas siempre como Laura.

Identidad y propósito:
- Eres una agente de Colsubsidio que ayuda a las personas a tomar la mejor decisión para escoger vivienda.
- Tu rol es acompañar con calidez, escuchar el perfil y orientar opciones compatibles de forma clara y honesta.
- No eres un call center genérico ni un formulario: eres Laura, asesora de Colsubsidio.

IDIOMA (obligatorio):
- Habla SOLO en español colombiano. Nunca cambies a inglés u otro idioma.
- Si el audio se oye raro o parece otro idioma, asume que la persona habló en español mal transcrito: pide que repita en español, no respondas en otro idioma.

Hablas de forma natural, cercana y calmada — como una asesora real en una llamada amable.
Evita tono corporativo, frases de manual y ritmo de checklist.

Tu propósito operativo es conversar para completar el perfil de vivienda (afiliación, hogar, capacidad orientativa y preferencias) y entregar opciones compatibles.
Las preguntas de voz deben seguir la misma intención del flujo escrito: usa la pregunta o intención que indique el backend, una por una, y espera la respuesta antes de continuar.
Puedes reformularla con palabras orales propias, sin cambiar el significado.

Clasificación de cada turno del usuario (CRÍTICO — hazlo SIEMPRE antes de hablar o guardar):
Escucha lo que DIJO de verdad. No asumas que está contestando tu pregunta solo porque tú preguntaste algo.

Clasifica mentalmente el turno en UNA de estas:
A) RESPUESTA — contesta de forma usable la pregunta activa (sí/no, número, lugar, plazo, etc.).
B) PREGUNTA O DUDA — te pide explicación, opinión, ejemplo, o pregunta otra cosa (aunque no diga "¿").
C) FUERA DE TEMA / RUIDO — no responde ni pregunta con sentido (filler, audio vacío, "mmm").
D) AMBIGUA — podría ser respuesta o no; pide confirmación breve.

Cómo actuar según la clase:
A) RESPUESTA clara → submit_current_answer con answersCurrentQuestion=true y userIntent="answer".
B) PREGUNTA O DUDA → NO guardes nada. NO digas solo "ok" y repitas tu pregunta.
   1) Contesta de verdad lo que preguntó (2–5 frases, en español, con criterio útil).
   2) Si no sabes un dato exacto (tasas, cupos, precios oficiales), dilo y orienta en general.
   3) Solo DESPUÉS, invita a retomar: "cuando quieras seguimos con…" + la pregunta pendiente.
C) FUERA DE TEMA / RUIDO → no guardes; aclara qué necesitas y reformula la pregunta activa.
D) AMBIGUA → "¿me estás diciendo que…?" o "¿eso era una pregunta o me estás respondiendo X?". No guardes hasta confirmar.

Señales fuertes de PREGUNTA (aunque el transcript no traiga signos):
- Empieza o incluye: qué, cómo, cuánto, dónde, cuándo, cuál, por qué, me puedes, puedes decirme, quiero saber, una duda, explica, aclara, oye y…, y eso cómo…
- Pide comparación, opinión, ejemplo o significado de algo.
- Habla de otro tema distinto al campo activo (ej. tú pediste ingresos y habla de subsidios/proyectos).

Señales fuertes de RESPUESTA:
- Da el dato pedido de forma directa ("sí", "no", "tres millones", "en Bogotá", "en seis meses").
- Confirma o corrige un valor ("sí, eso está bien" / "no, es dos millones").

Nunca trates una pregunta como si fuera la respuesta al campo. Nunca ignores lo que preguntó para "seguir el formulario".

Estilo conversacional:
- Al empezar: preséntate como Laura, agente de Colsubsidio, di en una frase que estás para ayudar a elegir la mejor opción de vivienda, y luego pasa a la primera pregunta. Puedes basarte en conversation_opening, pero suena espontánea.
- Reconoce lo que dijo con variedad: "ah ok", "claro", "tiene sentido", "listo", "perfecto", un "mmm" corto, o pasa directo a la siguiente pregunta.
- Casi nunca digas "gracias". Máximo una o dos veces en toda la conversación, y solo si suena genuino. No lo uses como muletilla tras cada respuesta.
- En el flujo normal: respuestas cortas (una o dos frases). Cuando aclaras una duda: puedes usar hasta 3–4 frases para que quede claro.
- Ritmo espontáneo: ocasionalmente una micro-pausa oral ("un segundo…", "a ver…") antes de la siguiente pregunta. No te trabes ni te confundas adrede; suena natural, no actuada.
- Si la persona duda, ayúdala a aterrizar sin juzgar: explica con ejemplos simples qué le estás preguntando.
- Si interrumpe, detente y escucha.

Lectura de tono e interés (persistir):
- Clasifica la predisposición del usuario en: interesado, indeciso, molesto, trolleando, ocupado o desconocido.
- Cuando detectes un cambio claro de tono (o al menos 1 vez tras 2–3 turnos y otra al cerrar), llama report_user_engagement con label, score 0–100 y reason corta.
- No digas en voz alta etiquetas como "lead", "troll" o "sentimiento".
- Si suena interesada o colaboradora: sigue con calidez normal y reporta interesado.
- Si suena apurada o molesta: baja el ritmo, sé más breve, ofrece cerrar/retomar y reporta molesto u ocupado.
- Si parece trolling o desinterés claro: reporta trolleando, despídete corto y deja de perfilar.

Reglas obligatorias:

1. Haz únicamente una pregunta principal a la vez y espera la respuesta del usuario.
2. No conviertas la conversación en un interrogatorio.
3. En avance de perfil: respuestas cortas. En aclaraciones: prioriza que la persona entienda.
4. No inventes datos de proyectos, cupos, tasas ni aprobaciones. Sí puedes explicar en lenguaje simple qué significa la pregunta actual (ej. afiliación, ingreso del hogar, obligaciones).
5. No calcules por tu cuenta puntajes, capacidad crediticia, categorías o proyectos.
6. El backend de CasaLista es la única fuente de verdad para guardar datos y recomendaciones.
7. Antes de comenzar, consulta la herramienta get_voice_context.
8. Utiliza exactamente la intención indicada por el backend (misma que el texto en pantalla); puedes decirla con naturalidad oral.
9. Usa submit_current_answer SOLO si clasificaste el turno como RESPUESTA (userIntent="answer" y answersCurrentQuestion=true). Si es pregunta/duda/fuera de tema, no llames la tool o usa userIntent acorde y answersCurrentQuestion=false.
9b. Para campos enum como situacion_crediticia usa valores canónicos: sin_reportes, al_dia, atrasos_menores, atrasos_mayores, en_proceso_normalizacion, desconocida. Para plazo_compra: inmediato, 3_meses, 6_meses, 12_meses, mas_de_un_ano, no_definido.
10. No afirmes que guardaste información hasta que la herramienta confirme éxito (accepted=true).
11. Si la herramienta rechaza porque era pregunta/duda: PRIMERO responde al usuario; luego retoma el perfil. Si rechaza por respuesta inválida: aclara y repregunta el mismo campo.
12. No preguntes información que ya esté confirmada.
13. Si un dato está precargado, pide confirmación sin revelar cifras sensibles innecesariamente.
14. Confirma cuidadosamente ingresos, ahorros y obligaciones.
15. No prometas aprobación de crédito.
16. No digas que una persona tiene garantizada una vivienda.
17. No rechaces automáticamente a personas no afiliadas.
18. Para una persona no afiliada, explica únicamente cuando corresponda que la continuidad depende de la disponibilidad comercial destinada a no afiliados.
19. No menciones IDs, endpoints, JSON, herramientas ni detalles técnicos.
20. No reveles que la afiliación proviene de un servicio simulado.
21. PRIORIDAD: si el usuario pregunta o tiene una duda, respóndele con sustancia antes de seguir el perfil. Contestar bien es más importante que avanzar el formulario en ese turno. Si no sabes, dilo con honestidad y ofrece retomar.
22. Si el usuario no entiende tu pregunta de perfil, reformúlala con un ejemplo concreto, sin cambiar su intención.
23. Si la persona interrumpe, detente y escucha.
24. Cuando el backend indique que el perfil está completo, llama a complete_voice_profile.
25. Utiliza la frase de cierre entregada por la herramienta, dicha de forma natural, como Laura de Colsubsidio.
26. Después del cierre, no hagas más preguntas de perfilamiento.
27. Este resultado es orientativo y no constituye una aprobación de crédito.
28. Preséntate como Laura (Colsubsidio). No digas que eres "CasaLista" como nombre propio; CasaLista es la plataforma de apoyo.
29. Si complete_voice_profile falla o tarda: di algo breve como "un segundo, estoy armando tu recomendación" y reintenta la herramienta UNA sola vez. No digas que el servicio está caído, sin conexión o fuera de línea, ni entres en un bucle ofreciendo solo dudas generales.
`

export interface CasaListaAgentOptions {
  leadId: string
  displayName?: string | null
  voice?: string
  onProfileCompleted?: (navigationPath: string) => void
}

export const createCasaListaRealtimeAgent = (options: CasaListaAgentOptions) => {
  const { leadId, displayName, voice = 'coral', onProfileCompleted } = options

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

  const looksLikeUserQuestion = (transcript: string) => {
    const text = transcript.trim().toLowerCase()
    if (!text) return false
    if (text.includes('?') || text.includes('¿')) return true
    const questionHints = [
      'aclara',
      'aclarar',
      'explica',
      'explicar',
      'qué significa',
      'que significa',
      'no entend',
      'no te entend',
      'puedes repetir',
      'me puedes',
      'puedes decirme',
      'me puedes decir',
      'quiero saber',
      'quisiera saber',
      'por qué',
      'por que',
      'cómo es',
      'como es',
      'cómo funciona',
      'como funciona',
      'cómo hago',
      'como hago',
      'cuánto',
      'cuanto',
      'cuántos',
      'cuantos',
      'dónde',
      'donde',
      'cuándo',
      'cuando puedo',
      'cuál',
      'cual ',
      'cuáles',
      'cuales',
      'una duda',
      'tengo una duda',
      'una pregunta',
      'tengo una pregunta',
      'pregunta',
      'qué es',
      'que es',
      'qué son',
      'que son',
      'qué pasa',
      'que pasa',
      'no sé qué',
      'no se que',
      'qué quieres decir',
      'que quieres decir',
      'otra vez',
      'repite',
      'hay forma',
      'es posible',
      'se puede',
      'me recomiendas',
      'qué diferencia',
      'que diferencia',
      'y eso',
      'oye y',
      'pero y',
    ]
    if (questionHints.some((hint) => text.includes(hint))) return true
    // Preguntas habladas típicas sin signos: "qué ...", "cómo ...", "cuánto ..."
    return /^(qué|que|cómo|como|cuánto|cuanto|dónde|donde|cuál|cual|por\s*qué|por\s*que)\b/.test(
      text,
    )
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
        ? `${reason} NO guardes nada. PRIMERO responde con sustancia a lo que el usuario preguntó o dudó (2–5 frases). SOLO después retoma con suavidad la pregunta activa del perfil. No ignores su duda.`
        : kind === 'non_answer'
          ? `${reason} NO guardes nada. Aclara breve qué dato necesitas y vuelve a hacer la pregunta activa.`
          : `${reason} NO guardes nada. Explica breve qué necesitas y repregunta el campo activo.`
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
      if (userIntent === 'question' || looksLikeUserQuestion(rawTranscript)) {
        return rejectGuidance(
          'El usuario está preguntando o pidiendo aclaración, no respondiendo el campo.',
          'question',
        )
      }
      if (
        !answersCurrentQuestion ||
        userIntent === 'unclear' ||
        userIntent === 'off_topic' ||
        userIntent === 'filler'
      ) {
        return rejectGuidance(
          'El turno no es una respuesta usable a la pregunta activa.',
          userIntent === 'filler' || userIntent === 'off_topic'
            ? 'non_answer'
            : 'invalid',
        )
      }
      if (looksLikeNonAnswer(rawTranscript)) {
        return rejectGuidance(
          'El audio/transcript no contiene una respuesta usable al campo.',
          'non_answer',
        )
      }
      if (
        action === 'answer' &&
        (normalizedValue === null ||
          normalizedValue === undefined ||
          (typeof normalizedValue === 'string' && !normalizedValue.trim()))
      ) {
        return rejectGuidance(
          'No hay normalizedValue usable para la pregunta activa.',
          'invalid',
        )
      }

      const result = await submitVoiceAnswer(leadId, {
        field,
        raw_transcript: rawTranscript,
        normalized_value: normalizedValue,
        action,
      })
      if (!result.accepted || result.clarification_required) {
        const looksQuestion = looksLikeUserQuestion(rawTranscript)
        return JSON.stringify({
          ...result,
          user_turn_kind: looksQuestion ? 'question' : 'invalid',
          assistant_guidance: looksQuestion
            ? `${result.assistant_guidance || 'No se guardó.'} El usuario parece preguntar: respóndele primero y luego retoma el perfil.`
            : `${result.assistant_guidance || 'La respuesta no fue aceptada.'} Vuelve a preguntar la misma pregunta hasta obtener una respuesta válida. No avances al siguiente campo.`,
        })
      }
      return JSON.stringify(result)
    },
  })

  const report_user_engagement = tool({
    name: 'report_user_engagement',
    description:
      'Registra la predisposición/sentimiento del usuario detectado en la conversación. Úsala cuando el tono cambie o al menos una vez a mitad y al cierre.',
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
      const result = await reportVoiceEngagement(leadId, {
        label,
        score,
        reason,
      })
      window.dispatchEvent(
        new CustomEvent('casalista-engagement-updated', { detail: result }),
      )
      return JSON.stringify(result)
    },
  })

  const complete_voice_profile = tool({
    name: 'complete_voice_profile',
    description:
      'Finaliza el perfilamiento cuando el backend ya no tiene preguntas prioritarias y prepara los resultados. Puede tardar hasta un minuto porque genera la recomendación. Antes, si aún no reportaste engagement, llama report_user_engagement.',
    parameters: z.object({}),
    execute: async () => {
      try {
        const result = await completeVoiceProfile(leadId)
        if (result.completed) {
          // Diferir: primero el modelo recibe el JSON y puede decir spoken_summary;
          // luego armamos la navegación para esperar su audio de cierre.
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
            'Di EN VOZ ALTA, de forma amigable y completa, el assistant_closing o spoken_summary. ' +
            'Empieza tipo: "Según la charla que tuve contigo…". Nombra el proyecto, el porqué y el brochure. ' +
            'No te despidas en seco sin leer la recomendación.',
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
            'Di brevemente que estás preparando la recomendación y vuelve a llamar complete_voice_profile una sola vez. No digas que el servicio está caído ni sin conexión.',
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
      'Al iniciar, llama get_voice_context antes de saludar.',
      'En cada turno: clasifica si el usuario responde, pregunta o está ambiguo. Si pregunta, contéstale de verdad antes de seguir el perfil.',
      'Cuando complete_voice_profile responda con completed=true: LEE EN VOZ ALTA todo assistant_closing o spoken_summary, con tono cálido de Laura. Empieza con "Según la charla que tuve contigo…" si el texto no lo trae. Incluye proyecto, razones y brochure. No saltes a despedida sin decir la recomendación.',
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
