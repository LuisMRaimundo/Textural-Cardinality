from __future__ import annotations

import pytest

from textural_cardinality.cardinality import (
    vertical_cardinality_for_notes,
    vertical_cardinality_from_summary_row,
)


def test_summary_row_does_not_infer_pc_cardinality() -> None:
    row = {"Notes": 2, "Unique pitches": 2}
    card = vertical_cardinality_from_summary_row(row, bin_cents=100, edo=12)
    assert card["vertical_note_count"] == 2
    assert card["vertical_unique_pitch_count"] == 2
    assert card["vertical_pitch_class_cardinality"] is None


def test_explicit_pc_cardinality_is_preserved() -> None:
    row = {"Notes": 2, "Unique pitches": 2, "PC cardinality": 1}
    card = vertical_cardinality_from_summary_row(row, bin_cents=100, edo=12)
    assert card["vertical_pitch_class_cardinality"] == 1


def test_c4_c5_has_one_pitch_class() -> None:
    notes = [("C", 0.0, 4), ("C", 0.0, 5)]
    card = vertical_cardinality_for_notes(notes, bin_cents=100, edo=12)
    assert card["vertical_note_count"] == 2
    assert card["vertical_unique_pitch_count"] == 2
    assert card["vertical_pitch_class_cardinality"] == 1


def test_24_edo_distinguishes_quarter_tone_pitch_classes() -> None:
    notes = [("C", 0.0, 4), ("C", 0.5, 4)]
    card = vertical_cardinality_for_notes(notes, bin_cents=50, edo=24)
    assert card["vertical_note_count"] == 2
    assert card["vertical_pitch_class_cardinality"] == 2


def test_48_edo_distinguishes_eighth_tone_pitch_classes() -> None:
    notes = [("C", 0.0, 4), ("C", 0.25, 4), ("C", 0.5, 4)]
    card = vertical_cardinality_for_notes(notes, bin_cents=25, edo=48)
    assert card["vertical_note_count"] == 3
    assert card["vertical_pitch_class_cardinality"] == 3


def test_12_edo_default_preserves_chromatic_pitch_class_cardinality() -> None:
    notes = [("C", 0.0, 4), ("C", 0.0, 5)]
    implicit = vertical_cardinality_for_notes(notes)
    explicit = vertical_cardinality_for_notes(notes, edo=12)
    assert implicit == explicit
    assert explicit["vertical_pitch_class_cardinality"] == 1


def test_invalid_edo_raises() -> None:
    with pytest.raises(ValueError):
        vertical_cardinality_for_notes([("C", 0.0, 4)], edo=0)


def test_24_edo_c_and_c_sharp_are_two_steps_apart() -> None:
    notes = [("C", 0.0, 4), ("C", 1.0, 4)]
    card = vertical_cardinality_for_notes(notes, bin_cents=50, edo=24)
    assert card["vertical_pitch_class_cardinality"] == 2
