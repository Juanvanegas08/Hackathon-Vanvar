"""Enrich catalog projects with structured brochure fichas.

Pipeline:
1. Download Heyzine PDF
2. Extract text (PyMuPDF / pypdf)
3. If text is weak, OCR pages via OpenAI Vision
4. Structure a ficha JSON with OpenAI (precio, entrega, tipologías, beneficios)

Usage:
    python scripts/enrich_project_fichas.py
    python scripts/enrich_project_fichas.py --limit 3
    python scripts/enrich_project_fichas.py --only-missing
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
from pypdf import PdfReader

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings  # noqa: E402

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    fitz = None  # type: ignore[assignment]

CATALOG_PATH = BACKEND_ROOT / "data" / "processed" / "projects_catalog.json"
FICHAS_PATH = BACKEND_ROOT / "data" / "processed" / "projects_fichas.json"
FRONTEND_BROCHURES = (
    BACKEND_ROOT.parent / "frontend" / "src" / "data" / "brochures.ts"
)

FICHA_SCHEMA_HINT = """
Devuelve SOLO JSON válido con esta forma:
{
  "nombre_comercial": "string|null",
  "ubicacion": "string|null",
  "municipio": "string|null",
  "direccion": "string|null",
  "precio_desde": number|null,
  "precio_hasta": number|null,
  "moneda": "COP",
  "fecha_entrega": "string|null",
  "estado_obra": "string|null",
  "acabados_entrega": "string|null",
  "tipologias": [
    {
      "nombre": "string",
      "area_m2": number|null,
      "habitaciones": number|null,
      "banos": number|null,
      "precio_desde": number|null,
      "precio_hasta": number|null,
      "notas": "string|null"
    }
  ],
  "unidades_totales": number|null,
  "torres": number|null,
  "pisos": number|null,
  "beneficios": ["subsidio VIS", "..."],
  "amenidades": ["parqueadero", "..."],
  "cerca_de": ["colegio", "..."],
  "resumen": "2 a 4 frases en español con lo esencial del proyecto",
  "datos_faltantes": ["precio", "entrega"]
}
Reglas:
- No inventes. Si no aparece, usa null o [].
- Precios en pesos colombianos numéricos sin puntos ni símbolos.
- fecha_entrega puede ser año, trimestre o texto del brochure (ej. "2026", "inmediata").
- Incluye subsidios VIS/VIP, certificación EDGE, etc. en beneficios cuando existan.
""".strip()

SKIP_NAMES = {"MULTIPROYECTO", "REVISTA"}


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enrich project fichas from brochures")
    parser.add_argument("--limit", type=int, default=0, help="Max projects with brochure")
    parser.add_argument(
        "--only-missing",
        action="store_true",
        help="Skip projects that already have metadata.ficha",
    )
    parser.add_argument(
        "--skip-frontend",
        action="store_true",
        help="Do not regenerate frontend brochures.ts",
    )
    return parser.parse_args()


def find_pdf_url(html: str) -> str | None:
    match = re.search(r"https?://cdn[^\"'\s]+\.pdf", html)
    if match:
        return match.group(0).replace("\\/", "/")
    match = re.search(r"https?://[^\"'\s]+\.pdf", html)
    return match.group(0).replace("\\/", "/") if match else None


def extract_text_pypdf(pdf_bytes: bytes, *, max_pages: int = 12) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    chunks: list[str] = []
    for page in reader.pages[:max_pages]:
        text = page.extract_text() or ""
        cleaned = re.sub(r"\s+", " ", text).strip()
        if cleaned:
            chunks.append(cleaned)
    return " ".join(chunks)


def extract_text_pymupdf(pdf_bytes: bytes, *, max_pages: int = 12) -> str:
    if fitz is None:
        return ""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    chunks: list[str] = []
    try:
        for index, page in enumerate(doc):
            if index >= max_pages:
                break
            text = page.get_text("text") or ""
            cleaned = re.sub(r"\s+", " ", text).strip()
            if cleaned:
                chunks.append(cleaned)
    finally:
        doc.close()
    return " ".join(chunks)


def render_page_pngs(pdf_bytes: bytes, *, max_pages: int = 4, zoom: float = 1.6) -> list[bytes]:
    if fitz is None:
        return []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images: list[bytes] = []
    try:
        matrix = fitz.Matrix(zoom, zoom)
        for index, page in enumerate(doc):
            if index >= max_pages:
                break
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            images.append(pix.tobytes("png"))
    finally:
        doc.close()
    return images


def openai_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def openai_ocr_images(
    client: httpx.Client,
    *,
    api_key: str,
    model: str,
    images: list[bytes],
    project_name: str,
) -> str:
    if not images:
        return ""
    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                f"Extrae TODO el texto visible del brochure del proyecto '{project_name}'. "
                "Devuelve solo texto plano en español, sin markdown. "
                "Incluye precios, áreas, tipologías, entrega, amenidades y beneficios."
            ),
        }
    ]
    for image in images:
        b64 = base64.b64encode(image).decode("ascii")
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"},
            }
        )
    body = {
        "model": model,
        "temperature": 0,
        "messages": [{"role": "user", "content": content}],
    }
    response = client.post(
        "https://api.openai.com/v1/chat/completions",
        headers=openai_headers(api_key),
        json=body,
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    return str(
        data.get("choices", [{}])[0].get("message", {}).get("content") or ""
    ).strip()


def openai_structure_ficha(
    client: httpx.Client,
    *,
    api_key: str,
    model: str,
    project: dict[str, Any],
    raw_text: str,
) -> dict[str, Any]:
    user_payload = {
        "proyecto_catalogo": {
            "nombre": project.get("nombre"),
            "ubicacion": project.get("ubicacion"),
            "municipio": project.get("municipio"),
            "valor_minimo": project.get("valor_minimo"),
            "valor_maximo": project.get("valor_maximo"),
            "etapa": project.get("etapa"),
            "brochure_url": project.get("brochure_url"),
        },
        "texto_brochure": raw_text[:12000],
        "instrucciones": FICHA_SCHEMA_HINT,
    }
    body = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Eres un extractor de fichas inmobiliarias en Colombia. "
                    "No inventes datos. Responde solo JSON."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False),
            },
        ],
    }
    response = client.post(
        "https://api.openai.com/v1/chat/completions",
        headers=openai_headers(api_key),
        json=body,
        timeout=90,
    )
    response.raise_for_status()
    data = response.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content") or "{}"
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("Ficha OpenAI no es un objeto JSON")
    return parsed


def compact_summary(text: str, *, limit: int = 2200) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def slugify(value: str) -> str:
    text = value.lower().strip()
    repl = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
        "ü": "u",
    }
    for src, dst in repl.items():
        text = text.replace(src, dst)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "proyecto"


def format_money(value: Any) -> str | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return f"${number:,.0f}".replace(",", ".")


def enrich_one(
    client: httpx.Client,
    project: dict[str, Any],
    *,
    api_key: str,
    model: str,
) -> dict[str, Any]:
    nombre = str(project.get("nombre") or "")
    report: dict[str, Any] = {
        "nombre": nombre,
        "brochure_url": project.get("brochure_url"),
        "status": "skipped",
        "ocr_used": False,
        "ficha": None,
    }
    if nombre.strip().upper() in SKIP_NAMES:
        report["status"] = "skipped_non_project"
        return report
    brochure_url = project.get("brochure_url")
    if not brochure_url:
        report["status"] = "no_brochure"
        return report

    html_resp = client.get(str(brochure_url), follow_redirects=True, timeout=45)
    html_resp.raise_for_status()
    pdf_url = find_pdf_url(html_resp.text)
    if not pdf_url:
        report["status"] = "pdf_not_found"
        return report
    report["pdf_url"] = pdf_url

    pdf_resp = client.get(pdf_url, follow_redirects=True, timeout=90)
    pdf_resp.raise_for_status()
    pdf_bytes = pdf_resp.content

    raw_text = extract_text_pymupdf(pdf_bytes) or extract_text_pypdf(pdf_bytes)
    source = "heyzine_pdf_text"
    if len(raw_text) < 180:
        images = render_page_pngs(pdf_bytes, max_pages=4)
        ocr_text = openai_ocr_images(
            client,
            api_key=api_key,
            model=model,
            images=images,
            project_name=nombre,
        )
        if ocr_text:
            raw_text = ocr_text
            source = "heyzine_pdf_ocr_openai"
            report["ocr_used"] = True

    if len(raw_text.strip()) < 40:
        report["status"] = "empty_text"
        return report

    ficha = openai_structure_ficha(
        client,
        api_key=api_key,
        model=model,
        project=project,
        raw_text=raw_text,
    )
    # Prefer historical catalog prices when brochure lacks them.
    if ficha.get("precio_desde") is None and project.get("valor_minimo") is not None:
        ficha["precio_desde"] = project.get("valor_minimo")
    if ficha.get("precio_hasta") is None and project.get("valor_maximo") is not None:
        ficha["precio_hasta"] = project.get("valor_maximo")
    if not ficha.get("ubicacion"):
        ficha["ubicacion"] = project.get("ubicacion") or project.get("municipio")

    summary = compact_summary(str(ficha.get("resumen") or raw_text))
    metadata = dict(project.get("metadata") or {})
    metadata.update(
        {
            "brochure_pdf_url": pdf_url,
            "brochure_summary": summary,
            "brochure_source": source,
            "ficha": ficha,
            "descripcion": summary[:500],
        }
    )
    project["metadata"] = metadata
    project["descripcion"] = summary[:500]
    if ficha.get("precio_desde") is not None and project.get("valor_minimo") is None:
        project["valor_minimo"] = ficha.get("precio_desde")
    if ficha.get("precio_hasta") is not None and project.get("valor_maximo") is None:
        project["valor_maximo"] = ficha.get("precio_hasta")
    if ficha.get("ubicacion") and not project.get("ubicacion"):
        project["ubicacion"] = ficha.get("ubicacion")
        project["municipio"] = ficha.get("municipio") or ficha.get("ubicacion")

    report["status"] = "ok"
    report["ficha"] = ficha
    report["brochure_summary"] = summary
    return report


def write_frontend_brochures(catalog: list[dict[str, Any]]) -> None:
    """Regenerate brochures.ts with enriched ficha fields when URL matches."""
    if not FRONTEND_BROCHURES.exists():
        print(f"Skip frontend: no existe {FRONTEND_BROCHURES}")
        return

    by_url: dict[str, dict[str, Any]] = {}
    for project in catalog:
        url = project.get("brochure_url")
        if url:
            by_url[str(url).rstrip("/")] = project

    # Keep existing cover images / order from current TS by parsing URLs.
    current = FRONTEND_BROCHURES.read_text(encoding="utf-8")
    existing_blocks = re.findall(
        r"\{\s*id:\s*'([^']+)'\s*,\s*ubicacion:\s*'((?:\\'|[^'])*)'\s*,\s*"
        r"proyecto:\s*'((?:\\'|[^'])*)'\s*,\s*url:\s*'([^']+)'\s*,\s*"
        r"coverImage:\s*'([^']+)'",
        current,
        flags=re.S,
    )

    lines: list[str] = [
        "export interface BrochureItem {",
        "  id: string",
        "  ubicacion: string",
        "  proyecto: string",
        "  url: string",
        "  /** Portada (primera página) del flipbook Heyzine. */",
        "  coverImage: string",
        "  precioDesde?: number | null",
        "  precioHasta?: number | null",
        "  fechaEntrega?: string | null",
        "  beneficios?: string[]",
        "  tipologiasResumen?: string | null",
        "  resumen?: string | null",
        "}",
        "",
        "/** Brochures enriquecidos desde PDF/OCR + ficha estructurada. */",
        "export const BROCHURES: BrochureItem[] = [",
    ]

    for item_id, ubicacion, proyecto, url, cover in existing_blocks:
        project = by_url.get(url.rstrip("/"))
        ficha = ((project or {}).get("metadata") or {}).get("ficha") or {}
        tipologias = ficha.get("tipologias") or []
        tipologias_resumen = None
        if tipologias:
            bits: list[str] = []
            for tip in tipologias[:3]:
                if not isinstance(tip, dict):
                    continue
                name = tip.get("nombre") or "Tipo"
                area = tip.get("area_m2")
                bits.append(f"{name}" + (f" ({area} m²)" if area else ""))
            tipologias_resumen = ", ".join(bits) if bits else None

        precio_desde = ficha.get("precio_desde")
        precio_hasta = ficha.get("precio_hasta")
        if precio_desde is None and project:
            precio_desde = project.get("valor_minimo")
        if precio_hasta is None and project:
            precio_hasta = project.get("valor_maximo")

        resumen = ficha.get("resumen") or ((project or {}).get("metadata") or {}).get(
            "brochure_summary"
        )
        beneficios = ficha.get("beneficios") or []
        fecha = ficha.get("fecha_entrega")

        def esc(value: str) -> str:
            return value.replace("\\", "\\\\").replace("'", "\\'")

        lines.append("  {")
        lines.append(f"    id: '{esc(item_id)}',")
        lines.append(f"    ubicacion: '{esc(ubicacion)}',")
        lines.append(f"    proyecto: '{esc(proyecto)}',")
        lines.append(f"    url: '{esc(url)}',")
        lines.append(f"    coverImage: '{esc(cover)}',")
        if precio_desde is not None:
            lines.append(f"    precioDesde: {float(precio_desde)},")
        if precio_hasta is not None:
            lines.append(f"    precioHasta: {float(precio_hasta)},")
        if fecha:
            lines.append(f"    fechaEntrega: '{esc(str(fecha))}',")
        if beneficios:
            ben = ", ".join(f"'{esc(str(b))}'" for b in beneficios[:6])
            lines.append(f"    beneficios: [{ben}],")
        if tipologias_resumen:
            lines.append(f"    tipologiasResumen: '{esc(tipologias_resumen)}',")
        if resumen:
            short = re.sub(r"\s+", " ", str(resumen)).strip()[:280]
            lines.append(f"    resumen: '{esc(short)}',")
        lines.append("  },")

    lines.append("]")
    lines.append("")
    FRONTEND_BROCHURES.write_text("\n".join(lines), encoding="utf-8")
    print(f"Actualizado: {FRONTEND_BROCHURES}")


def main() -> int:
    _configure_stdout()
    args = parse_args()
    settings = get_settings()
    api_key = settings.openai_api_key
    if not api_key:
        print("Falta OPENAI_API_KEY para OCR/estructuración.")
        return 1
    model = settings.openai_recommender_model or "gpt-4.1-mini"

    if not CATALOG_PATH.exists():
        print(f"No existe catálogo: {CATALOG_PATH}")
        return 1
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(catalog, list):
        print("Catálogo inválido")
        return 1

    reports: list[dict[str, Any]] = []
    processed = 0
    with httpx.Client(headers={"User-Agent": "CasaListaFichaEnricher/1.0"}) as client:
        for project in catalog:
            if not project.get("brochure_url"):
                reports.append(
                    {
                        "nombre": project.get("nombre"),
                        "status": "no_brochure",
                    }
                )
                continue
            if args.only_missing and (project.get("metadata") or {}).get("ficha"):
                reports.append(
                    {
                        "nombre": project.get("nombre"),
                        "status": "already_enriched",
                    }
                )
                continue
            if args.limit and processed >= args.limit:
                break
            processed += 1
            try:
                report = enrich_one(
                    client,
                    project,
                    api_key=api_key,
                    model=model,
                )
            except Exception as exc:  # noqa: BLE001
                report = {
                    "nombre": project.get("nombre"),
                    "status": f"error:{type(exc).__name__}",
                    "error": str(exc)[:240],
                }
            reports.append(report)
            print(
                f"{report.get('status')}"
                f"{' [ocr]' if report.get('ocr_used') else ''}: "
                f"{report.get('nombre')}"
            )

    CATALOG_PATH.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    FICHAS_PATH.write_text(
        json.dumps(
            {
                "model": model,
                "ok_count": sum(1 for item in reports if item.get("status") == "ok"),
                "ocr_count": sum(1 for item in reports if item.get("ocr_used")),
                "projects": reports,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Actualizado: {CATALOG_PATH}")
    print(f"Reporte: {FICHAS_PATH}")

    if not args.skip_frontend:
        write_frontend_brochures(catalog)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
