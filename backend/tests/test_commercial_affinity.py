"""Tests for commercial housing-affinity helpers."""

from app.utils.commercial_affinity import (
    AffinityBand,
    build_commercial_snapshot,
    classify_affinity,
    parse_commercial_snapshot,
)


def test_classify_affinity_bands() -> None:
    assert classify_affinity(70) == AffinityBand.LISTO
    assert classify_affinity(100) == AffinityBand.LISTO
    assert classify_affinity(69.9) == AffinityBand.POR_EVALUAR
    assert classify_affinity(30) == AffinityBand.POR_EVALUAR
    assert classify_affinity(29.9) == AffinityBand.BAJA_AFINIDAD
    assert classify_affinity(None) is None


def test_commercial_snapshot_roundtrip() -> None:
    snap = build_commercial_snapshot(
        affinity_percent=82.456,
        top_project_id="mongui",
        top_project_name="Monguí",
    )
    assert snap["affinity_percent"] == 82.46
    assert snap["affinity_band"] == "listo"
    parsed = parse_commercial_snapshot(snap)
    assert parsed is not None
    assert parsed["top_project_name"] == "Monguí"
    assert parse_commercial_snapshot({"foo": 1}) is None
