"""Inspect Excel datasets provided for the housing hackathon.

Usage:
    python scripts/inspect_data.py --buyers "RUTA_ARCHIVO" --brochures "RUTA_ARCHIVO"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

# Allow running as `python scripts/inspect_data.py` from backend/
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.utils.normalization import normalize_for_comparison  # noqa: E402

COLUMN_HINTS: dict[str, tuple[str, ...]] = {
    "proyecto": ("proyecto", "project", "nombre proyecto", "desarrollo"),
    "afiliacion": ("afili", "caja", "colsubsidio"),
    "segmento": ("segmento", "segment"),
    "salario": ("salario", "ingreso", "sueldo", "rango salarial"),
    "personas_a_cargo": ("cargo", "beneficiar", "dependen", "personas"),
    "empresa": ("empresa", "empleador", "razon social"),
    "entidad_financiera": ("entidad", "banco", "financiera", "credito"),
    "valor_vivienda": ("valor", "precio", "vivienda", "avaluo"),
    "fecha_opcion": ("opcion", "opción", "fecha opcion"),
    "fecha_desistimiento": ("desist", "fecha desist"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspecciona archivos Excel del reto de vivienda sin modificarlos.",
    )
    parser.add_argument("--buyers", type=str, help="Ruta al Excel de compradores históricos")
    parser.add_argument("--brochures", type=str, help="Ruta al Excel de brochures/links")
    parser.add_argument(
        "--extra",
        type=str,
        nargs="*",
        default=[],
        help="Rutas adicionales de Excel a inspeccionar",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Imprime el reporte completo en JSON",
    )
    return parser.parse_args()


def detect_related_columns(columns: list[str]) -> dict[str, list[str]]:
    detected: dict[str, list[str]] = {key: [] for key in COLUMN_HINTS}
    for column in columns:
        normalized = normalize_for_comparison(column) or ""
        for key, hints in COLUMN_HINTS.items():
            if any(hint in normalized for hint in hints):
                detected[key].append(column)
    return {key: values for key, values in detected.items() if values}


def inspect_sheet(df: pd.DataFrame, sheet_name: str) -> dict[str, Any]:
    null_pct = {
        str(col): round(float(df[col].isna().mean() * 100), 2) for col in df.columns
    }
    dtypes = {str(col): str(dtype) for col, dtype in df.dtypes.items()}
    unique_preview: dict[str, list[Any]] = {}
    for col in df.columns:
        series = df[col].dropna()
        if series.empty:
            unique_preview[str(col)] = []
            continue
        # Limit uniqueness exploration for free-text heavy columns.
        uniques = series.astype(str).value_counts().head(8)
        unique_preview[str(col)] = [
            {"value": idx, "count": int(count)} for idx, count in uniques.items()
        ]

    columns = [str(c) for c in df.columns]
    return {
        "sheet": sheet_name,
        "rows": int(len(df)),
        "columns_count": int(len(df.columns)),
        "columns": columns,
        "dtypes": dtypes,
        "null_percentage": null_pct,
        "top_unique_values": unique_preview,
        "related_columns": detect_related_columns(columns),
    }


def inspect_tabular(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "error": "Archivo no encontrado"}
    suffix = path.suffix.lower()
    if suffix == ".csv" or suffix not in {".xlsx", ".xls", ".xlsm"}:
        try:
            df = pd.read_csv(path)
            return {
                "path": str(path),
                "sheet_names": ["csv"],
                "sheets": [inspect_sheet(df, "csv")],
            }
        except Exception as exc:  # noqa: BLE001 - report load errors to the operator
            if suffix == ".csv":
                return {"path": str(path), "error": f"No se pudo leer CSV: {exc}"}
    return inspect_excel(path)


def inspect_excel(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "error": "Archivo no encontrado"}
    workbook = pd.ExcelFile(path)
    sheets = []
    for sheet_name in workbook.sheet_names:
        df = pd.read_excel(workbook, sheet_name=sheet_name)
        sheets.append(inspect_sheet(df, sheet_name))
    return {
        "path": str(path),
        "sheet_names": list(workbook.sheet_names),
        "sheets": sheets,
    }


def print_human_report(report: dict[str, Any]) -> None:
    if "error" in report:
        print(f"\n[ERROR] {report['path']}: {report['error']}")
        return

    print(f"\n=== Archivo: {report['path']} ===")
    print(f"Hojas: {', '.join(report['sheet_names'])}")
    for sheet in report["sheets"]:
        print(f"\n-- Hoja: {sheet['sheet']} --")
        print(f"Filas: {sheet['rows']} | Columnas: {sheet['columns_count']}")
        print("Columnas:")
        for column in sheet["columns"]:
            dtype = sheet["dtypes"].get(column, "?")
            null_pct = sheet["null_percentage"].get(column, 0)
            print(f"  - {column} | tipo={dtype} | nulos={null_pct}%")
        if sheet["related_columns"]:
            print("Columnas relacionadas detectadas:")
            for key, cols in sheet["related_columns"].items():
                print(f"  - {key}: {', '.join(cols)}")
        print("Valores únicos principales (top):")
        for column, values in sheet["top_unique_values"].items():
            if not values:
                continue
            preview = ", ".join(f"{item['value']} ({item['count']})" for item in values[:5])
            print(f"  - {column}: {preview}")


def _configure_stdout() -> None:
    """Avoid Windows cp1252 crashes when printing accented data."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    _configure_stdout()
    args = parse_args()
    paths: list[Path] = []
    if args.buyers:
        paths.append(Path(args.buyers))
    if args.brochures:
        paths.append(Path(args.brochures))
    paths.extend(Path(item) for item in args.extra)

    if not paths:
        print("Debe indicar al menos una ruta con --buyers, --brochures o --extra.")
        return 1

    reports = [inspect_tabular(path) for path in paths]
    if args.json:
        print(json.dumps(reports, ensure_ascii=False, indent=2))
    else:
        for report in reports:
            print_human_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
