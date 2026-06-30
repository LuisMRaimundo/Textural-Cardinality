"""Shared pitch-grid primitives for symbolic cardinality analysis."""

from __future__ import annotations

import math

NoteTuple = tuple[str, float, int]

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
    return 12.0 * (octave + 1) + _STEP_TO_SEMITONE[step.upper()] + alter


def _pitch_unit(note: NoteTuple, *, bin_cents: float) -> int:
    cents = _midi_from_note_tuple(note) * 100.0
    return int(round(cents / float(bin_cents)))


def _pc_class(note: NoteTuple, *, edo: int = 12) -> int:
    edo = validate_edo(edo)
    ps = _midi_from_note_tuple(note)
    return int(round(ps * float(edo) / 12.0)) % edo
