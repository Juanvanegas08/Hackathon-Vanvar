"""OpenAI-backed project recommendation provider (no hardcoded ranking rules)."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import ConfigurationError, RealtimeServiceError
from app.models.lead import Lead
from app.models.project import Project

logger = logging.getLogger(__name__)

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"

SYSTEM_PROMPT = """
Eres Laura, asesora inmobiliaria de Colsubsidio (Colombia) en la plataforma CasaLista.
Ayudas a las personas a tomar la mejor decisión para escoger vivienda.
Recibes el perfil completo de una persona y un catálogo de proyectos con
ubicación, precios históricos, etapa, brochure, ficha (tipologías/m²/habitaciones),
pros/contras derivados de datos históricos y situación crediticia declarada.

Debes elegir las mejores opciones SIN inventar datos que no estén en el input.
Usa brochure_summary / descripcion / ficha cuando existan para justificar la recomendación
con hechos del proyecto (ubicación, tipología, precios, entrega, amenidades, beneficios).
No apruebes crédito. No garantices cupo. Sé transparente y breve.

Criterios OBLIGATORIOS de decisión (en este orden de prioridad):
1) Tamaño del hogar ↔ tamaño del apartamento (CRÍTICO):
   - Usa personas_hogar (y personas_a_cargo si aporta contexto).
   - Guía orientativa de tipología mínima:
     * 1–2 personas: prioriza 1–2 habitaciones / ~40–55 m² cuando existan en ficha.
     * 3–4 personas: prioriza 2–3 habitaciones / ~50–70 m².
     * 5 o más personas: prioriza 3+ habitaciones / ~65+ m²; evita aptos muy pequeños.
   - Si ficha.tipologias existe, elige o menciona la tipología más adecuada al hogar.
   - Si el proyecto no trae habitaciones/m², bájale el score y dilo en cons/reason.
   - En reason y spoken_summary DEBES mencionar el cruce hogar ↔ tipología/tamaño
     (ej. "viven 4 personas y este proyecto ofrece tipologías de 2–3 alcobas").
2) Capacidad económica: salario/ingreso_hogar, ahorro, obligaciones y precios
   (ficha.precio_desde/hasta o valor_minimo/maximo / histórico).
3) Ubicación: prioriza ubicacion_deseada; si no hay match exacto, cercanía razonable.
4) Plazo de compra y etapa/entrega del proyecto (ficha.fecha_entrega si existe).
5) Afiliación/beneficios (VIS, EDGE, etc.) sin excluir no afiliados.
6) Brochure disponible: prioriza proyectos con brochure_url/ficha.

Responde SOLO JSON válido con esta forma exacta:
{
  "recommendations": [
    {
      "project_id": "uuid-string",
      "project_name": "nombre exacto del catálogo",
      "rank": 1,
      "probability": 0.0,
      "compatibility_score": 0,
      "reason": "una razón clara y concreta para esta persona, citando datos del perfil y del brochure/catálogo (incluye hogar vs tipología)",
      "pros": ["..."],
      "cons": ["..."],
      "brochure_url": "https://..."
    }
  ],
  "best_project_id": "uuid-string o null",
  "spoken_summary": "texto oral amigable en español colombiano, en primera persona como Laura"
}

Reglas:
- probability entre 0 y 1 (orientativa, no es probabilidad estadística real).
- compatibility_score entre 0 y 100; penaliza fuerte si el apto es claramente pequeño para el hogar.
- Máximo N recomendaciones pedidas.
- Prioriza proyectos con brochure_url cuando existan.
- La reason debe explicar por qué encaja con ESTE perfil (hogar/tamaño, ingresos, ubicación deseada, afiliación, plazo).
- Si la persona no afiliada, no la excluyas; menciona que la continuidad comercial depende de disponibilidad.
- spoken_summary DEBE sonar a Laura hablando en voz alta (3 a 6 frases), cálida y clara. Estructura obligatoria:
  1) Apertura: "Según la charla que tuve contigo, y después de revisar los proyectos del catálogo, mi recomendación es…"
  2) Nombrar el proyecto #1 y por qué encaja (hogar vs tipología/m², ubicación, precio/VIS si aplica).
  3) Mencionar el brochure en voz natural ("puedes revisar el brochure en este enlace: …") si hay brochure_url.
  4) Nombrar 1–2 alternativas cortas.
  5) Cerrar con que es orientativo, no una aprobación de crédito.
- No uses jerga técnica ni digas "spoken_summary", "JSON" o "motor".
""".strip()


class OpenAIRecommendationProvider:
    """Ask OpenAI to rank projects for a lead profile."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._http_client = http_client

    @property
    def enabled(self) -> bool:
        return bool(
            self._settings.openai_recommender_enabled
            and self._settings.openai_api_key
        )

    def recommend(
        self,
        lead: Lead,
        projects: list[Project],
        *,
        limit: int = 3,
        profile_document: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.enabled:
            raise ConfigurationError(
                "El recomendador OpenAI no está habilitado o falta OPENAI_API_KEY."
            )
        if not projects:
            return {
                "recommendations": [],
                "best_project_id": None,
                "spoken_summary": (
                    "Todavía no tengo proyectos con brochure disponibles "
                    "para recomendarte."
                ),
            }

        payload_projects = [
            self._project_payload(project) for project in projects
        ]
        user_payload = {
            "perfil": profile_document
            or {
                "lead_id": str(lead.id),
                "nombre": lead.nombre,
                "afiliado": lead.afiliado,
                "categoria_afiliacion": getattr(
                    lead.categoria_afiliacion, "value", lead.categoria_afiliacion
                ),
                "empresa": lead.empresa,
                "salario_mensual": lead.salario_mensual,
                "ingreso_hogar": lead.ingreso_hogar,
                "ahorro": lead.ahorro,
                "obligaciones_mensuales": lead.obligaciones_mensuales,
                "situacion_crediticia": getattr(
                    lead.situacion_crediticia, "value", lead.situacion_crediticia
                ),
                "personas_hogar": lead.personas_hogar,
                "personas_a_cargo": lead.personas_a_cargo,
                "tiene_vivienda": lead.tiene_vivienda,
                "ubicacion_actual": lead.ubicacion_actual,
                "ubicacion_deseada": lead.ubicacion_deseada,
                "plazo_compra": getattr(lead.plazo_compra, "value", lead.plazo_compra),
                "proyecto_interes": lead.proyecto_interes,
            },
            "limite": max(1, min(limit, 10)),
            "proyectos": payload_projects,
            "instrucciones": (
                "Elige las mejores opciones para este perfil. "
                "OBLIGATORIO: cruza personas_hogar con ficha.tipologias "
                "(habitaciones/area_m2) y explícalo en reason y spoken_summary. "
                "También pondera ingresos vs precio, ubicación deseada, plazo/entrega, "
                "afiliación/beneficios y brochure. "
                "Incluye razón por proyecto y un spoken_summary final "
                "con nombre + por qué + link del brochure."
            ),
        }

        body = {
            "model": self._settings.openai_recommender_model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(user_payload, ensure_ascii=False),
                },
            ],
        }

        try:
            response = self._request(body)
        except httpx.TimeoutException as exc:
            raise RealtimeServiceError(
                "El recomendador tardó demasiado en responder.",
                code="recommender_timeout",
            ) from exc
        except httpx.HTTPError as exc:
            raise RealtimeServiceError(
                "No fue posible obtener recomendaciones con OpenAI.",
                code="recommender_unavailable",
            ) from exc

        if response.status_code in {401, 403}:
            raise RealtimeServiceError(
                "No fue posible autenticar el recomendador OpenAI.",
                code="recommender_unauthorized",
            )
        if response.status_code == 429:
            raise RealtimeServiceError(
                "El recomendador alcanzó su límite temporal.",
                code="recommender_rate_limited",
            )
        if response.status_code >= 400:
            logger.warning(
                "OpenAI recommender error status=%s body=%s",
                response.status_code,
                response.text[:500],
            )
            raise RealtimeServiceError(
                "El recomendador OpenAI respondió con error.",
                code="recommender_error",
            )

        data = response.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "{}")
        )
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RealtimeServiceError(
                "La respuesta del recomendador no es JSON válido.",
                code="recommender_invalid_json",
            ) from exc

        if not isinstance(parsed, dict):
            raise RealtimeServiceError(
                "La respuesta del recomendador tiene formato inesperado.",
                code="recommender_invalid_payload",
            )
        return parsed

    def _project_payload(self, project: Project) -> dict[str, Any]:
        profile = project.perfil_historico
        pros: list[str] = []
        cons: list[str] = []

        if project.brochure_url:
            pros.append("Tiene brochure disponible para revisar.")
        else:
            cons.append("No tiene brochure cargado en el catálogo.")

        if project.ubicacion or project.municipio:
            pros.append(
                f"Ubicación catalogada: {project.ubicacion or project.municipio}."
            )
        else:
            cons.append("Ubicación incompleta en catálogo.")

        if profile.historical_price_median is not None:
            pros.append(
                f"Precio histórico mediano aproximado: "
                f"{profile.historical_price_median:,.0f}."
            )
        elif project.valor_minimo is not None:
            pros.append(f"Valor mínimo observado: {project.valor_minimo:,.0f}.")
        else:
            cons.append("Sin precio confiable en catálogo.")

        if profile.affiliated_percentage is not None:
            pros.append(
                f"Participación histórica afiliados: {profile.affiliated_percentage}%."
            )
        if profile.withdrawal_percentage is not None and profile.withdrawal_percentage > 20:
            cons.append(
                f"Desistimientos históricos altos: {profile.withdrawal_percentage}%."
            )
        if profile.total_buyers:
            pros.append(f"Muestra histórica: {profile.total_buyers} compradores.")
        else:
            cons.append("Sin muestra histórica emparejada.")

        if profile.frequent_financial_entities:
            pros.append(
                "Entidades financieras frecuentes: "
                + ", ".join(profile.frequent_financial_entities[:3])
            )

        return {
            "project_id": str(project.id),
            "project_name": project.nombre,
            "ubicacion": project.ubicacion,
            "municipio": project.municipio,
            "departamento": project.departamento,
            "etapa": project.etapa,
            "valor_minimo": project.valor_minimo,
            "valor_maximo": project.valor_maximo,
            "brochure_url": project.brochure_url,
            "recorrido_360_url": project.recorrido_360_url,
            "disponible": project.disponible,
            "descripcion": project.metadata.get("descripcion")
            or project.metadata.get("brochure_summary"),
            "brochure_summary": project.metadata.get("brochure_summary"),
            "brochure_pdf_url": project.metadata.get("brochure_pdf_url"),
            "ficha": project.metadata.get("ficha"),
            "fechas_contexto": {
                "etapa": project.etapa,
                "fecha_entrega_brochure": (
                    (project.metadata.get("ficha") or {}).get("fecha_entrega")
                ),
                "nota": (
                    "Usa ficha.fecha_entrega cuando exista; si no, etapa/histórico."
                ),
            },
            "precio": {
                "valor_minimo": project.valor_minimo,
                "valor_maximo": project.valor_maximo,
                "brochure_precio_desde": (
                    (project.metadata.get("ficha") or {}).get("precio_desde")
                ),
                "brochure_precio_hasta": (
                    (project.metadata.get("ficha") or {}).get("precio_hasta")
                ),
                "historico_min": profile.historical_price_min,
                "historico_max": profile.historical_price_max,
                "historico_mediana": profile.historical_price_median,
                "precio_confiable": profile.historical_price_reliable,
            },
            "vida_crediticia_contexto": {
                "entidades_financieras_frecuentes": profile.frequent_financial_entities,
                "nota": (
                    "No hay buró crediticio del lead; solo situación declarada "
                    "en el perfil y entidades históricas del proyecto."
                ),
            },
            "perfil_historico": {
                "total_buyers": profile.total_buyers,
                "affiliated_percentage": profile.affiliated_percentage,
                "non_affiliated_percentage": profile.non_affiliated_percentage,
                "salary_range_distribution": profile.salary_range_distribution,
                "segments": profile.segments,
                "dependents_distribution": profile.dependents_distribution,
                "household_composition_distribution": (
                    profile.household_composition_distribution
                ),
                "frequent_locations": profile.frequent_locations,
                "withdrawal_percentage": profile.withdrawal_percentage,
            },
            "pros": pros,
            "cons": cons,
            "aliases": project.metadata.get("aliases", []),
        }

    def _request(self, payload: dict[str, Any]) -> httpx.Response:
        headers = {
            "Authorization": f"Bearer {self._settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        timeout = self._settings.openai_request_timeout_seconds
        if self._http_client is not None:
            return self._http_client.post(
                OPENAI_CHAT_URL,
                headers=headers,
                json=payload,
                timeout=timeout,
            )
        with httpx.Client(timeout=timeout) as client:
            return client.post(OPENAI_CHAT_URL, headers=headers, json=payload)
