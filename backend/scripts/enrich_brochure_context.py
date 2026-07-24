"""Enrich projects_catalog.json with brochure text extracted from Heyzine PDFs.

Usage:
    python scripts/enrich_brochure_context.py
"""

from __future__ import annotations

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

CATALOG_PATH = BACKEND_ROOT / "data" / "processed" / "projects_catalog.json"
CONTEXT_PATH = BACKEND_ROOT / "data" / "processed" / "projects_brochure_context.json"


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def find_pdf_url(html: str) -> str | None:
    match = re.search(r"https?://cdn[^\"'\s]+\.pdf", html)
    if match:
        return match.group(0).replace("\\/", "/")
    match = re.search(r"https?://[^\"'\s]+\.pdf", html)
    return match.group(0).replace("\\/", "/") if match else None


def extract_pdf_text(pdf_bytes: bytes, *, max_pages: int = 8) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    chunks: list[str] = []
    for page in reader.pages[:max_pages]:
        text = page.extract_text() or ""
        cleaned = re.sub(r"\s+", " ", text).strip()
        if cleaned:
            chunks.append(cleaned)
    return " ".join(chunks)


def summarize_brochure_text(text: str, *, limit: int = 1800) -> str:
    if not text:
        return ""
    # Keep readable excerpt for LLM context.
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def enrich_project(client: httpx.Client, project: dict[str, Any]) -> dict[str, Any]:
    brochure_url = project.get("brochure_url")
    metadata = dict(project.get("metadata") or {})
    result = {
        "nombre": project.get("nombre"),
        "brochure_url": brochure_url,
        "pdf_url": None,
        "brochure_summary": None,
        "status": "skipped",
    }
    if not brochure_url:
        result["status"] = "no_brochure"
        return result

    try:
        html_resp = client.get(str(brochure_url), follow_redirects=True, timeout=45)
        html_resp.raise_for_status()
        pdf_url = find_pdf_url(html_resp.text)
        if not pdf_url:
            result["status"] = "pdf_not_found"
            return result
        result["pdf_url"] = pdf_url
        pdf_resp = client.get(pdf_url, follow_redirects=True, timeout=60)
        pdf_resp.raise_for_status()
        raw_text = extract_pdf_text(pdf_resp.content)
        summary = summarize_brochure_text(raw_text)
        if not summary:
            result["status"] = "empty_text"
            return result
        metadata["brochure_pdf_url"] = pdf_url
        metadata["brochure_summary"] = summary
        metadata["brochure_source"] = "heyzine_pdf"
        project["metadata"] = metadata
        # Optional short description field for human/LLM readability.
        project["descripcion"] = summary[:500]
        result["brochure_summary"] = summary
        result["status"] = "ok"
        return result
    except Exception as exc:  # noqa: BLE001
        result["status"] = f"error:{type(exc).__name__}"
        result["error"] = str(exc)[:200]
        return result


def main() -> int:
    _configure_stdout()
    if not CATALOG_PATH.exists():
        print(f"No existe catálogo: {CATALOG_PATH}")
        return 1

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(catalog, list):
        print("El catálogo no es una lista JSON.")
        return 1

    reports: list[dict[str, Any]] = []
    with httpx.Client(headers={"User-Agent": "CasaListaBrochureEnricher/1.0"}) as client:
        for project in catalog:
            report = enrich_project(client, project)
            reports.append(report)
            print(f"{report['status']}: {report.get('nombre')}")

    CATALOG_PATH.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    CONTEXT_PATH.write_text(
        json.dumps(
            {
                "source_catalog": str(CATALOG_PATH),
                "projects": reports,
                "ok_count": sum(1 for item in reports if item["status"] == "ok"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Actualizado: {CATALOG_PATH}")
    print(f"Reporte: {CONTEXT_PATH}")
    print(f"OK: {sum(1 for item in reports if item['status'] == 'ok')}/{len(reports)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
