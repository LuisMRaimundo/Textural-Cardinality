"""Score-driven vertical cardinality analysis."""

from __future__ import annotations

from collections import Counter
import csv
import json
import math
import tempfile
from typing import Any

from music21 import converter
from music21.chord import Chord
from music21.note import Note
from music21.pitch import Pitch
from music21.stream import Score

NoteTuple = tuple[str, float, int]
_EPS = 1e-9
SUPPORTED_EDOS = {12, 24, 48}
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
    if edo not in SUPPORTED_EDOS:
        raise ValueError("edo must be one of: 12, 24, 48")
    return edo


def _nearest_int(x: float) -> int:
    return int(math.floor(float(x) + 0.5 + 1e-9))


def _pitch_to_note_tuple(p: Pitch) -> NoteTuple | None:
    if p.octave is None:
        return None
    step = str(p.step).upper()
    octave = int(p.octave)
    base_ps = 12.0 * (octave + 1) + _STEP_TO_SEMITONE[step]
    alter = float(p.ps) - base_ps
    return (step, alter, octave)


def _midi_from_note_tuple(note: NoteTuple) -> float:
    step, alter, octave = note[0], float(note[1]), int(note[2])
    return 12.0 * (octave + 1) + _STEP_TO_SEMITONE[step.upper()] + alter


def _pitch_unit(note: NoteTuple, *, bin_cents: int) -> int:
    cents = _midi_from_note_tuple(note) * 100.0
    return int(round(cents / float(bin_cents)))


def _pc_class(note: NoteTuple, *, edo: int = 12) -> int:
    edo = validate_edo(edo)
    ps = _midi_from_note_tuple(note)
    if edo == 12:
        # Preserve existing 12-EDO behaviour as closely as possible.
        return int(round(ps)) % 12
    step = (ps % 12.0) * edo / 12.0
    return _nearest_int(step) % edo


def _collect_events(
    score: Score,
    *,
    edo: int = 12,
    bin_cents: int = 100,
) -> tuple[list[dict[str, Any]], float]:
    edo = validate_edo(edo)
    events: list[dict[str, Any]] = []
    end_time = 0.0
    for el in score.recurse().notes:
        # Use score-global offset (not local measure/voice offset).
        offset = float(el.getOffsetInHierarchy(score))
        duration = float(el.duration.quarterLength) if el.duration is not None else 0.0
        end = offset + max(0.0, duration)
        pitches: list[NoteTuple] = []
        if isinstance(el, Note):
            nt = _pitch_to_note_tuple(el.pitch)
            if nt is not None:
                pitches.append(nt)
        elif isinstance(el, Chord):
            for p in el.pitches:
                nt = _pitch_to_note_tuple(p)
                if nt is not None:
                    pitches.append(nt)
        if not pitches:
            continue
        events.append(
            {
                "offset": offset,
                "end": end,
                "notes": pitches,
                "units": [_pitch_unit(n, bin_cents=bin_cents) for n in pitches],
                "pcs": [_pc_class(n, edo=edo) for n in pitches],
            }
        )
        end_time = max(end_time, end)
    return events, end_time


def _time_axis(end_time: float, time_step: float) -> list[float]:
    step = max(1e-6, float(time_step))
    t = 0.0
    out: list[float] = []
    while t <= end_time + 1e-9:
        out.append(round(t, 6))
        t += step
    if not out:
        out.append(0.0)
    return out


def _build_cardinality_series(times: list[float], events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not times:
        return []

    starts = sorted(events, key=lambda ev: (float(ev["offset"]), float(ev["end"])))
    ends = sorted(events, key=lambda ev: (float(ev["end"]), float(ev["offset"])))
    si = 0
    ei = 0

    active_note_count = 0
    active_units: Counter[int] = Counter()
    active_pcs: Counter[int] = Counter()

    series: list[dict[str, Any]] = []
    for t in times:
        while ei < len(ends) and float(ends[ei]["end"]) + _EPS <= t:
            ev = ends[ei]
            active_note_count -= len(ev["notes"])
            for unit in ev["units"]:
                active_units[unit] -= 1
                if active_units[unit] <= 0:
                    del active_units[unit]
            for pc in ev["pcs"]:
                active_pcs[pc] -= 1
                if active_pcs[pc] <= 0:
                    del active_pcs[pc]
            ei += 1

        while si < len(starts) and float(starts[si]["offset"]) <= t + _EPS:
            ev = starts[si]
            active_note_count += len(ev["notes"])
            active_units.update(ev["units"])
            active_pcs.update(ev["pcs"])
            si += 1

        series.append(
            {
                "time_quarters": t,
                "vertical_note_count": int(active_note_count),
                "vertical_unique_pitch_count": int(len(active_units)),
                "vertical_pitch_class_cardinality": int(len(active_pcs)),
            }
        )
    return series


def analyze_vertical_cardinality(
    score_path: str,
    *,
    time_step: float = 0.25,
    edo: int = 12,
    bin_cents: int = 100,
) -> dict[str, Any]:
    edo = validate_edo(edo)
    score = converter.parse(score_path)
    events, end_time = _collect_events(score, edo=edo, bin_cents=bin_cents)
    times = _time_axis(end_time, time_step)
    series = _build_cardinality_series(times, events)
    return {
        "source_file": str(score_path),
        "time_step": float(time_step),
        "duration_quarters": float(end_time),
        "event_count": len(events),
        "edo": edo,
        "pitch_class_universe": f"Z{edo}",
        "bin_cents": int(bin_cents),
        "series": series,
    }


def write_cardinality_csv(analysis: dict[str, Any]) -> str:
    with tempfile.NamedTemporaryFile(
        prefix="textural_dimension_cardinality_",
        suffix=".csv",
        delete=False,
    ) as tf:
        out_path = tf.name
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "time_quarters",
                "vertical_note_count",
                "vertical_unique_pitch_count",
                "vertical_pitch_class_cardinality",
            ],
        )
        w.writeheader()
        for row in analysis["series"]:
            w.writerow(row)
    return out_path


def write_cardinality_json(analysis: dict[str, Any]) -> str:
    with tempfile.NamedTemporaryFile(
        prefix="textural_dimension_cardinality_",
        suffix=".json",
        delete=False,
    ) as tf:
        out_path = tf.name
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    return out_path
