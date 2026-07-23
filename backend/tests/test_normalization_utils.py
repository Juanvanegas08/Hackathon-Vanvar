"""Tests for buyer export normalization helpers."""

from app.utils.normalization import (
    infer_affiliation_from_periodo,
    normalize_age_range_label,
    normalize_yes_no_flag,
    parse_money_value,
    scale_housing_value,
)


def test_scale_housing_value_divides_export_inflation() -> None:
    scaled, reliable, note = scale_housing_value(5_523_620_000_000)
    assert scaled == 552_362_000.0
    assert reliable is True
    assert note is not None
    assert "10000" in note


def test_scale_housing_value_keeps_plausible_amounts() -> None:
    scaled, reliable, note = scale_housing_value(250_000_000)
    assert scaled == 250_000_000.0
    assert reliable is True
    assert note is None


def test_normalize_yes_no_flag() -> None:
    assert normalize_yes_no_flag("Si") is True
    assert normalize_yes_no_flag("No") is False
    assert normalize_yes_no_flag("2/10/2024") is None


def test_infer_affiliation_from_periodo() -> None:
    assert infer_affiliation_from_periodo("2024-2") is True
    assert infer_affiliation_from_periodo("") is False
    assert infer_affiliation_from_periodo(None) is False


def test_normalize_age_range_label_unifies_variants() -> None:
    assert normalize_age_range_label("20 - 35 años") == "20 a 35 años"
    assert normalize_age_range_label("36 a 45 años") == "36 a 45 años"


def test_parse_money_value_us_thousands() -> None:
    amount, warning = parse_money_value("5,523,620,000,000")
    assert amount == 5_523_620_000_000.0
    assert warning is None
