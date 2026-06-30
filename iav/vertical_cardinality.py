"""
Symbolic vertical cardinality helpers.

Counts notated pitch events, pitch units, and pitch classes for one vertical
slice or summary row. Score-wide time series use event-boundary sampling in
``textural_cardinality.analysis``; see ``TECHNICAL_MANUAL.md`` §4.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from textural_cardinality.pitch_grid import (
    NoteTuple,
    TUNING_PRESETS,
    _STEP_TO_SEMITONE,
    _midi_from_note_tuple,
    _nearest_int,
    _pc_class,
    _pitch_unit,
    validate_edo,
)

VERTICAL_CARDINALITY_SCHEMA_VERSION = "1.0"


def vertical_cardinality_for_notes(
    notes: Sequence[NoteTuple],
    *,
    bin_cents: float = 100.0,
    edo: int = 12,
) -> dict[str, int | None]:
    """Cardinality metrics for one vertical slice (after caller-applied dedupe)."""
    edo = validate_edo(edo)
    n_events = len(notes)
    if n_events == 0:
        return {
            "vertical_note_count": 0,
            "vertical_unique_pitch_count": 0,
            "vertical_pitch_class_cardinality": 0,
        }
    units = {_pitch_unit(n, bin_cents=bin_cents) for n in notes}
    pcs = {_pc_class(n, edo=edo) for n in notes}
    return {
        "vertical_note_count": n_events,
        "vertical_unique_pitch_count": len(units),
        "vertical_pitch_class_cardinality": len(pcs),
    }


def vertical_cardinality_from_summary_row(
    row: Mapping[str, Any],
    *,
    bin_cents: float = 100.0,
    edo: int = 12,
) -> dict[str, int | None]:
    """
    Recover cardinality from a slice-summary row.

    ``vertical_pitch_class_cardinality`` is taken only from an explicit ``PC cardinality``
    column; it is never inferred from unique pitch count (octave duplicates break that identity).
    """
    del bin_cents
    validate_edo(edo)

    notes_raw = row.get("Notes")
    if notes_raw is None or notes_raw == "":
        vnc: int | None = None
    else:
        try:
            vnc = int(notes_raw)
        except (TypeError, ValueError):
            vnc = None

    unique_raw = row.get("Unique pitches")
    if unique_raw is None or unique_raw == "":
        vup: int | None = vnc if vnc is not None else None
    else:
        try:
            vup = int(unique_raw)
        except (TypeError, ValueError):
            vup = None

    pc_raw = row.get("PC cardinality")
    if pc_raw is None or pc_raw == "":
        vpc: int | None = None
    else:
        try:
            vpc = int(pc_raw)
        except (TypeError, ValueError):
            vpc = None

    return {
        "vertical_note_count": vnc,
        "vertical_unique_pitch_count": vup,
        "vertical_pitch_class_cardinality": vpc,
    }
