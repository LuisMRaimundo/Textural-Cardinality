from __future__ import annotations

from textural_dimension.cardinality import (
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
