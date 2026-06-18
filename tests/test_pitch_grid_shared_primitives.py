"""Shared pitch-grid primitive import compatibility."""

from __future__ import annotations

import iav.vertical_cardinality as iav_vc
import textural_dimension.analysis as analysis
import textural_dimension.pitch_grid as pitch_grid


def test_pitch_unit_is_shared_callable() -> None:
    assert analysis._pitch_unit is pitch_grid._pitch_unit
    assert iav_vc._pitch_unit is pitch_grid._pitch_unit


def test_pc_class_is_shared_callable() -> None:
    assert analysis._pc_class is pitch_grid._pc_class
    assert iav_vc._pc_class is pitch_grid._pc_class


def test_tuning_presets_are_shared_object() -> None:
    assert analysis.TUNING_PRESETS is pitch_grid.TUNING_PRESETS
    assert iav_vc.TUNING_PRESETS is pitch_grid.TUNING_PRESETS


def test_validate_edo_is_shared_callable() -> None:
    assert analysis.validate_edo is pitch_grid.validate_edo
    assert iav_vc.validate_edo is pitch_grid.validate_edo
    assert analysis.validate_edo(24) == pitch_grid.validate_edo(24) == iav_vc.validate_edo(24)
