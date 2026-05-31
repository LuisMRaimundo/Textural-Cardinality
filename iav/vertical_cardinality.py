"""
Symbolic vertical cardinality helpers.

Counts notated pitch events, pitch units, and pitch classes for one vertical
slice or summary row. Score-wide time series use event-boundary sampling in
``textural_dimension.analysis``; see ``TECHNICAL_MANUAL.md`` §4.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from typing import Any

NoteTuple = tuple[str, float, int]

VERTICAL_CARDINALITY_SCHEMA_VERSION = "1.0"
TUNING_PRESETS = {
    "12_edo": {"bin_cents": 100.0, "edo": 12},
    "24_edo": {"bin_cents": 50.0, "edo": 24},
    "48_edo": {"bin_cents": 25.0, "edo": 48},
    "31_edo": {"bin_cents": 38.70967741935484, "edo": 31},
    "19_edo": {"bin_cents": 63.15789473684211, "edo": 19},
    "53_edo": {"bin_cents": 22.641509433962263, "edo": 53},
}
_STEP_TO_SEMITONE = {
    "C": 0.0,
    "D": 2.0,
    "E": 4.0,
    "F": 5.0,
    "G": 7.0,
    "A": 9.0,
    "B": 11.0,
}


def validate_edo(edo: int) -> int:
    edo = int(edo)
    if edo <= 0:
        raise ValueError("edo must be a positive integer")
    return edo


def _nearest_int(x: float) -> int:
    return int(math.floor(float(x) + 0.5 + 1e-9))


def _midi_from_note_tuple(note: NoteTuple) -> float:
    step, alter, octave = note[0], float(note[1]), int(note[2])
    return 12.0 * (octave + 1) + _STEP_TO_SEMITONE[str(step).upper()] + alter


def _pitch_unit(note: NoteTuple, *, bin_cents: float) -> int:
    cents = _midi_from_note_tuple(note) * 100.0
    return int(round(cents / float(bin_cents)))


def _pc_class(note: NoteTuple, *, edo: int = 12) -> int:
    edo = validate_edo(edo)
    ps = _midi_from_note_tuple(note)
    return int(round(ps * float(edo) / 12.0)) % edo


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
