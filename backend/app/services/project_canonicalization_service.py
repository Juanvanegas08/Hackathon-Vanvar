"""Canonical project consolidation from catalog, profiles and aliases."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from app.core.config import Settings, get_settings
from app.models.project import HistoricalProfile, Project
from app.models.project_alias import CanonicalProject, ProjectAliasGroup
from app.utils.project_matching import (
    compare_project_names,
    core_project_key,
    normalize_project_name,
)


class ProjectCanonicalizationService:
    """Build and resolve canonical project identities."""

    def __init__(
        self,
        settings: Settings | None = None,
        aliases_path: str | Path | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        resolved_aliases = aliases_path or self._settings.project_aliases_path
        self._aliases_path = Path(str(resolved_aliases))
        self._alias_groups = self._load_alias_groups()
        self._alias_index = self._build_alias_index(self._alias_groups)

    def resolve_canonical_id(self, project_name: str) -> tuple[str, str, str]:
        """Return (canonical_id, canonical_name, match_kind)."""
        normalized = normalize_project_name(project_name) or ""
        if normalized in self._alias_index:
            group_id, group = self._alias_index[normalized]
            return group_id, group.canonical_name, "manual_alias"

        # Exact core-key match against known alias keys.
        core = core_project_key(project_name)
        if core and core in self._alias_index:
            group_id, group = self._alias_index[core]
            return group_id, group.canonical_name, "manual_alias_core"

        slug = self._slugify(project_name)
        return slug, project_name.strip(), "standalone"

    def consolidate(
        self,
        catalog: list[dict[str, Any]],
        profiles: list[dict[str, Any]] | None = None,
    ) -> tuple[list[CanonicalProject], dict[str, Any]]:
        """Consolidate catalog rows into canonical projects and build a report."""
        profiles = profiles or []
        profile_by_id = {
            str(item.get("project_id")): item
            for item in profiles
            if item.get("project_id")
        }
        profile_by_name = {
            normalize_project_name(str(item.get("catalog_name") or "")): item
            for item in profiles
            if item.get("catalog_name")
        }

        buckets: dict[str, dict[str, Any]] = {}
        report: dict[str, Any] = {
            "manual_aliases_applied": [],
            "automatic_matches": [],
            "ambiguous_candidates": [],
            "projects_without_alias": [],
            "pending_review": [],
            "consolidated": [],
        }

        # Detect automatic near-duplicates not covered by aliases.
        names = [str(item.get("nombre") or "") for item in catalog]
        for index, left in enumerate(names):
            for right in names[index + 1 :]:
                decision = compare_project_names(left, right)
                left_id, _, left_kind = self.resolve_canonical_id(left)
                right_id, _, right_kind = self.resolve_canonical_id(right)
                if left_id == right_id:
                    continue
                if decision.kind == "approximate":
                    report["pending_review"].append(
                        {
                            "left": left,
                            "right": right,
                            "score": decision.score,
                            "reason": "possible_duplicate_without_shared_alias",
                        }
                    )
                elif decision.kind == "ambiguous":
                    report["ambiguous_candidates"].append(
                        {"left": left, "right": right, "score": decision.score}
                    )

        for item in catalog:
            name = str(item.get("nombre") or "").strip()
            canonical_id, canonical_name, match_kind = self.resolve_canonical_id(name)
            bucket = buckets.setdefault(
                canonical_id,
                {
                    "canonical_project_id": canonical_id,
                    "name": canonical_name,
                    "aliases": set(),
                    "catalog_records": [],
                    "profiles": [],
                    "brochure_urls": [],
                    "tour_urls": [],
                    "available_flags": [],
                    "etapas": [],
                    "ubicaciones": [],
                    "municipios": [],
                    "departamentos": [],
                    "codigos": [],
                    "prices_min": [],
                    "prices_max": [],
                    "primary_catalog_id": None,
                    "metadata": {"match_kinds": [], "original_names": []},
                },
            )
            bucket["aliases"].add(name)
            bucket["catalog_records"].append(item)
            bucket["metadata"]["match_kinds"].append(match_kind)
            bucket["metadata"]["original_names"].append(name)
            if match_kind.startswith("manual"):
                report["manual_aliases_applied"].append(
                    {"name": name, "canonical_project_id": canonical_id}
                )
            elif match_kind == "standalone":
                report["projects_without_alias"].append(name)
            else:
                report["automatic_matches"].append(
                    {"name": name, "canonical_project_id": canonical_id, "kind": match_kind}
                )

            project_id = item.get("id")
            profile = None
            if project_id is not None:
                profile = profile_by_id.get(str(project_id))
            if profile is None:
                profile = profile_by_name.get(normalize_project_name(name) or "")
            if profile is not None:
                bucket["profiles"].append(profile)
                if bucket["primary_catalog_id"] is None and profile.get("total_buyers", 0):
                    bucket["primary_catalog_id"] = project_id
            if bucket["primary_catalog_id"] is None:
                bucket["primary_catalog_id"] = project_id

            if item.get("brochure_url"):
                bucket["brochure_urls"].append(item.get("brochure_url"))
            if item.get("recorrido_360_url"):
                bucket["tour_urls"].append(item.get("recorrido_360_url"))
            bucket["available_flags"].append(bool(item.get("disponible", True)))
            for key, store in (
                ("etapa", "etapas"),
                ("ubicacion", "ubicaciones"),
                ("municipio", "municipios"),
                ("departamento", "departamentos"),
                ("codigo", "codigos"),
            ):
                if item.get(key):
                    bucket[store].append(item.get(key))
            if item.get("valor_minimo") is not None:
                bucket["prices_min"].append(item.get("valor_minimo"))
            if item.get("valor_maximo") is not None:
                bucket["prices_max"].append(item.get("valor_maximo"))

            # Prefer nicer display names over ALL CAPS short aliases.
            if canonical_name.isupper() and not name.isupper() and len(name) > len(canonical_name):
                bucket["name"] = name

        canonical_projects: list[CanonicalProject] = []
        for canonical_id, bucket in sorted(buckets.items(), key=lambda item: item[0]):
            profile_data = bucket["profiles"]
            assert isinstance(profile_data, list)
            merged_profile = self._merge_profiles(profile_data)
            # Prefer alias group display name when available.
            if canonical_id in self._alias_groups:
                display_name = self._alias_groups[canonical_id].canonical_name
                aliases = sorted(
                    set(bucket["aliases"]) | set(self._alias_groups[canonical_id].aliases)
                )
            else:
                display_name = str(bucket["name"])
                aliases = sorted(bucket["aliases"])

            project = CanonicalProject(
                canonical_project_id=canonical_id,
                name=display_name,
                aliases=aliases,
                catalog_records=list(bucket["catalog_records"]),
                historical_profile=merged_profile,
                brochure_url=bucket["brochure_urls"][0] if bucket["brochure_urls"] else None,
                tour_360_url=bucket["tour_urls"][0] if bucket["tour_urls"] else None,
                available=any(bucket["available_flags"]) if bucket["available_flags"] else True,
                codigo=bucket["codigos"][0] if bucket["codigos"] else None,
                etapa=bucket["etapas"][0] if bucket["etapas"] else None,
                ubicacion=bucket["ubicaciones"][0] if bucket["ubicaciones"] else None,
                municipio=bucket["municipios"][0] if bucket["municipios"] else None,
                departamento=bucket["departamentos"][0] if bucket["departamentos"] else None,
                valor_minimo=min(bucket["prices_min"]) if bucket["prices_min"] else None,
                valor_maximo=max(bucket["prices_max"]) if bucket["prices_max"] else None,
                primary_catalog_id=(
                    UUID(str(bucket["primary_catalog_id"]))
                    if bucket["primary_catalog_id"]
                    else None
                ),
                metadata={
                    "original_names": bucket["metadata"]["original_names"],
                    "match_kinds": bucket["metadata"]["match_kinds"],
                    "catalog_count": len(bucket["catalog_records"]),
                    "historical_buyers": merged_profile.total_buyers,
                },
            )
            canonical_projects.append(project)
            report["consolidated"].append(
                {
                    "canonical_project_id": canonical_id,
                    "name": display_name,
                    "aliases": aliases,
                    "catalog_count": len(bucket["catalog_records"]),
                    "historical_buyers": merged_profile.total_buyers,
                }
            )

        report["summary"] = {
            "canonical_projects": len(canonical_projects),
            "manual_aliases_applied": len(report["manual_aliases_applied"]),
            "projects_without_alias": len(report["projects_without_alias"]),
            "pending_review": len(report["pending_review"]),
            "ambiguous_candidates": len(report["ambiguous_candidates"]),
        }
        return canonical_projects, report

    def to_project_models(self, canonical_projects: list[CanonicalProject]) -> list[Project]:
        """Map canonical projects into Project models for scoring reuse."""
        projects: list[Project] = []
        for item in canonical_projects:
            project_id = item.primary_catalog_id
            if project_id is None and item.catalog_records:
                raw_id = item.catalog_records[0].get("id")
                project_id = UUID(str(raw_id)) if raw_id else None
            if project_id is None:
                # Deterministic UUID5-like fallback from canonical id bytes is avoided;
                # use a nil-derived unique placeholder via uuid5 namespace.
                from uuid import NAMESPACE_URL, uuid5

                project_id = uuid5(NAMESPACE_URL, item.canonical_project_id)
            projects.append(
                Project(
                    id=project_id,
                    nombre=item.name,
                    codigo=item.codigo,
                    etapa=item.etapa,
                    ubicacion=item.ubicacion,
                    municipio=item.municipio,
                    departamento=item.departamento,
                    valor_minimo=item.valor_minimo,
                    valor_maximo=item.valor_maximo,
                    brochure_url=item.brochure_url,
                    recorrido_360_url=item.tour_360_url,
                    disponible=item.available,
                    perfil_historico=item.historical_profile,
                    metadata={
                        **item.metadata,
                        "canonical_project_id": item.canonical_project_id,
                        "aliases": item.aliases,
                    },
                )
            )
        return projects

    def _merge_profiles(self, profiles: list[dict[str, Any]]) -> HistoricalProfile:
        if not profiles:
            return HistoricalProfile()
        # Prefer the richest historical sample; do not double-count buyers.
        best = max(profiles, key=lambda item: int(item.get("total_buyers") or 0))
        return HistoricalProfile(
            total_buyers=int(best.get("total_buyers") or 0),
            affiliated_percentage=best.get("affiliated_percentage"),
            non_affiliated_percentage=best.get("non_affiliated_percentage"),
            category_distribution=best.get("category_distribution") or {},
            salary_range_distribution=best.get("salary_range_distribution") or {},
            segments=best.get("segments") or {},
            dependents_distribution=best.get("dependents_distribution") or {},
            dependents_average=best.get("dependents_average"),
            household_composition_distribution=(
                best.get("household_composition_distribution") or {}
            ),
            frequent_locations=best.get("frequent_locations") or [],
            frequent_financial_entities=best.get("frequent_financial_entities") or [],
            frequent_companies=best.get("frequent_companies") or [],
            enterprise_pyramid_distribution=best.get("enterprise_pyramid_distribution") or {},
            historical_price_min=best.get("historical_price_min"),
            historical_price_max=best.get("historical_price_max"),
            historical_price_median=best.get("historical_price_median"),
            historical_price_reliable=bool(best.get("historical_price_reliable", False)),
            withdrawal_percentage=best.get("withdrawal_percentage"),
            missing_data_percentage=best.get("missing_data_percentage") or {},
            age_range_distribution=best.get("age_range_distribution") or {},
        )

    def _load_alias_groups(self) -> dict[str, ProjectAliasGroup]:
        if not self._aliases_path.exists():
            return {}
        payload = json.loads(self._aliases_path.read_text(encoding="utf-8"))
        groups: dict[str, ProjectAliasGroup] = {}
        for key, value in payload.items():
            groups[key] = ProjectAliasGroup.model_validate(value)
        return groups

    def _build_alias_index(
        self,
        groups: dict[str, ProjectAliasGroup],
    ) -> dict[str, tuple[str, ProjectAliasGroup]]:
        index: dict[str, tuple[str, ProjectAliasGroup]] = {}
        for group_id, group in groups.items():
            candidates = [group.canonical_name, *group.aliases]
            for candidate in candidates:
                normalized = normalize_project_name(candidate)
                if normalized:
                    index[normalized] = (group_id, group)
                core = core_project_key(candidate)
                if core:
                    index[core] = (group_id, group)
            index[group_id.replace("_", " ")] = (group_id, group)
        return index

    @staticmethod
    def _slugify(value: str) -> str:
        normalized = normalize_project_name(value) or "proyecto"
        tokens = [token for token in normalized.split(" ") if token]
        return "_".join(tokens)[:80] or "proyecto"
