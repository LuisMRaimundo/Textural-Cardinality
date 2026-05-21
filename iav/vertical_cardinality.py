"""
Symbolic vertical cardinality (Interval Analyser–compatible API).

Counts notated pitch events / pitch units / pitch classes per vertical slice or summary row.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from music21.pitch import Accidental, Pitch

NoteTuple = tuple[str, float, int]

VERTICAL_CARDINALITY_SCHEMA_VERSION = "1.0"


def _midi_from_note_tuple(note: NoteTuple) -> float:
    step, alter, octave = note[0], float(note[1]), int(note[2])
    p = Pitch(step)
    p.octave = octave
    if alter:
        p.accidental = Accidental(alter)
    return float(p.ps)


def _pitch_unit(note: NoteTuple, *, bin_cents: int) -> int:
    cents = _midi_from_note_tuple(note) * 100.0
    return int(round(cents / float(bin_cents)))


def vertical_cardinality_for_notes(
    notes: Sequence[NoteTuple],
    *,
    bin_cents: int,
    edo: int,
) -> dict[str, int | None]:
    """Cardinality metrics for one vertical slice (after caller-applied dedupe)."""
    n_events = len(notes)
    if n_events == 0:
        return {
            "vertical_note_count": 0,
            "vertical_unique_pitch_count": 0,
            "vertical_pitch_class_cardinality": 0 if edo == 12 else None,
        }
    units = {_pitch_unit(n, bin_cents=bin_cents) for n in notes}
    unique_pitch = len(units)
    if edo == 12:
        pcs = {int(round(_midi_from_note_tuple(n))) % 12 for n in notes}
        pc_card: int | None = len(pcs)
    else:
        pc_card = None
    return {
        "vertical_note_count": n_events,
        "vertical_unique_pitch_count": unique_pitch,
        "vertical_pitch_class_cardinality": pc_card,
    }


def vertical_cardinality_from_summary_row(
    row: Mapping[str, Any],
    *,
    bin_cents: int,
    edo: int,
) -> dict[str, int | None]:
    """
    Recover cardinality from a slice-summary row.

    ``vertical_pitch_class_cardinality`` is taken only from an explicit ``PC cardinality``
    column; it is never inferred from unique pitch count (octave duplicates break that identity).
    """
    del bin_cents, edo

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
