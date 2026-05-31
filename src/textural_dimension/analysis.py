"""Score-driven vertical cardinality analysis.

Cardinality is evaluated instantaneously at score time *t* as the size of the
active note multiset. Because that function changes only at event onsets and
offsets, :func:`_time_axis` always includes those boundary times so brief
sonorities are not missed. An optional uniform ``time_step`` grid is merged in
for plotting convenience only.
"""

from __future__ import annotations

from collections import Counter
import csv
import json
import math
from pathlib import Path
import tempfile
from typing import Any

from music21 import converter
from music21.chord import Chord
from music21.note import Note
from music21.pitch import Pitch
from music21.stream import Score

NoteTuple = tuple[str, float, int]
_EPS = 1e-9
_TOL = 1e-6
DEFAULT_BIN_CENTS = 100.0
DEFAULT_EDO = 12
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


def validate_bin_cents(bin_cents: float) -> float:
    bin_cents = float(bin_cents)
    if bin_cents <= 0:
        raise ValueError("bin_cents must be > 0")
    return bin_cents


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


def _pitch_unit(note: NoteTuple, *, bin_cents: float) -> int:
    cents = _midi_from_note_tuple(note) * 100.0
    return int(round(cents / float(bin_cents)))


def _pc_class(note: NoteTuple, *, edo: int = 12) -> int:
    edo = validate_edo(edo)
    ps = _midi_from_note_tuple(note)
    return int(round(ps * float(edo) / 12.0)) % edo


def _is_multiple_of_step(value: float, step: float, tol: float = _TOL) -> bool:
    nearest = round(value / step)
    return abs(value - nearest * step) <= tol


def _iter_raw_pitches(events: list[dict[str, Any]]) -> list[tuple[int | None, float | None, float]]:
    out: list[tuple[int | None, float | None, float]] = []
    for ev in events:
        for rp in ev.get("raw_pitches", []):
            out.append((rp.get("part_index"), rp.get("beat"), float(rp["ps"])))
    return out


def _non_grid_pitches(
    events: list[dict[str, Any]],
    *,
    bin_cents: float,
    tol: float = _TOL,
) -> list[tuple[int | None, float | None, float]]:
    bad: list[tuple[int | None, float | None, float]] = []
    for part_index, beat, ps in _iter_raw_pitches(events):
        nearest = round((ps * 100.0) / bin_cents)
        snapped = (nearest * bin_cents) / 100.0
        if abs(ps - snapped) > tol:
            bad.append((part_index, beat, ps))
    return bad


def _requantize_events(events: list[dict[str, Any]], *, bin_cents: float, edo: int) -> None:
    for ev in events:
        pitches = ev["notes"]
        ev["units"] = [_pitch_unit(n, bin_cents=bin_cents) for n in pitches]
        ev["pcs"] = [_pc_class(n, edo=edo) for n in pitches]


def detect_tuning_grid(events: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Inspect every event pitch-space value and infer a compatible EDO grid.
    """
    raw = _iter_raw_pitches(events)
    if not raw:
        return {
            "detected_bin_cents": DEFAULT_BIN_CENTS,
            "detected_edo": DEFAULT_EDO,
            "tuning_preset_match": "12_edo",
            "non_grid_pitches": [],
        }

    fracs: list[float] = []
    for _, _, ps in raw:
        frac = ps - math.floor(ps)
        if abs(frac - 1.0) <= _TOL or abs(frac) <= _TOL:
            frac = 0.0
        fracs.append(frac)

    if all(abs(frac) <= _TOL for frac in fracs):
        return {
            "detected_bin_cents": DEFAULT_BIN_CENTS,
            "detected_edo": DEFAULT_EDO,
            "tuning_preset_match": "12_edo",
            "non_grid_pitches": [],
        }

    candidates = [
        ("24_edo", 0.5, 50.0, 24),
        ("48_edo", 0.25, 25.0, 48),
        (None, 1.0 / 3.0, 100.0 / 3.0, 36),
        (None, 1.0 / 6.0, 100.0 / 6.0, 72),
    ]
    for preset_name, step, bin_cents, edo in candidates:
        if all(_is_multiple_of_step(frac, step) for frac in fracs):
            return {
                "detected_bin_cents": float(bin_cents),
                "detected_edo": int(edo),
                "tuning_preset_match": preset_name,
                "non_grid_pitches": [],
            }

    best_edo: int | None = None
    for edo in range(2, 241):
        step = 12.0 / float(edo)
        if all(_is_multiple_of_step(frac, step) for frac in fracs):
            best_edo = edo
    if best_edo is not None:
        best_bin = 1200.0 / float(best_edo)
        preset_name: str | None = None
        for name, preset in TUNING_PRESETS.items():
            if (
                int(preset["edo"]) == best_edo
                and abs(float(preset["bin_cents"]) - best_bin) <= _TOL
            ):
                preset_name = name
                break
        return {
            "detected_bin_cents": best_bin,
            "detected_edo": best_edo,
            "tuning_preset_match": preset_name,
            "non_grid_pitches": [],
        }

    return {
        "detected_bin_cents": DEFAULT_BIN_CENTS,
        "detected_edo": DEFAULT_EDO,
        "tuning_preset_match": None,
        "non_grid_pitches": _non_grid_pitches(events, bin_cents=DEFAULT_BIN_CENTS),
    }


def _collect_events(
    score: Score,
    *,
    edo: int = 12,
    bin_cents: float = 100.0,
) -> tuple[list[dict[str, Any]], float]:
    edo = validate_edo(edo)
    bin_cents = validate_bin_cents(bin_cents)
    part_index_map: dict[int, int] = {id(part): i for i, part in enumerate(score.parts)}
    events: list[dict[str, Any]] = []
    end_time = 0.0
    for el in score.recurse().notes:
        # Use score-global offset (not local measure/voice offset).
        offset = float(el.getOffsetInHierarchy(score))
        duration = float(el.duration.quarterLength) if el.duration is not None else 0.0
        end = offset + max(0.0, duration)
        pitches: list[NoteTuple] = []
        raw_pitches: list[dict[str, Any]] = []
        part = el.getContextByClass("Part")
        part_index = part_index_map.get(id(part)) if part is not None else None
        beat_value = float(el.beat) if getattr(el, "beat", None) is not None else offset
        if isinstance(el, Note):
            nt = _pitch_to_note_tuple(el.pitch)
            if nt is not None:
                pitches.append(nt)
                raw_pitches.append(
                    {
                        "part_index": part_index,
                        "beat": beat_value,
                        "ps": float(el.pitch.ps),
                    }
                )
        elif isinstance(el, Chord):
            for p in el.pitches:
                nt = _pitch_to_note_tuple(p)
                if nt is not None:
                    pitches.append(nt)
                    raw_pitches.append(
                        {
                            "part_index": part_index,
                            "beat": beat_value,
                            "ps": float(p.ps),
                        }
                    )
        if not pitches:
            continue
        events.append(
            {
                "offset": offset,
                "end": end,
                "notes": pitches,
                "units": [_pitch_unit(n, bin_cents=bin_cents) for n in pitches],
                "pcs": [_pc_class(n, edo=edo) for n in pitches],
                "raw_pitches": raw_pitches,
            }
        )
        end_time = max(end_time, end)
    return events, end_time


def _time_axis(
    end_time: float,
    time_step: float | None,
    events: list[dict[str, Any]] | None = None,
) -> list[float]:
    """
    Build analysis times that include every vertical state change.

    Event onsets and offsets are always included so brief sonorities are not
    missed between coarse uniform grid points. When ``time_step`` is set, a
    regular grid is merged in for plotting convenience.
    """
    times: set[float] = {0.0}
    if end_time > 0.0:
        times.add(round(end_time, 6))

    if events:
        for ev in events:
            times.add(round(float(ev["offset"]), 6))
            times.add(round(float(ev["end"]), 6))

    if time_step is not None:
        step = max(1e-6, float(time_step))
        t = 0.0
        while t <= end_time + 1e-9:
            times.add(round(t, 6))
            t += step

    if not times:
        times.add(0.0)
    return sorted(times)


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
    time_step: float | None = 0.25,
    edo: int = DEFAULT_EDO,
    bin_cents: float = DEFAULT_BIN_CENTS,
    auto_detect_tuning: bool = False,
    tuning_preset: str | None = None,
    debug_export_internal_path: bool = False,
) -> dict[str, Any]:
    edo = validate_edo(edo)
    bin_cents = validate_bin_cents(bin_cents)
    if tuning_preset is not None and tuning_preset not in TUNING_PRESETS:
        raise ValueError(f"Unknown tuning_preset: {tuning_preset}")

    score = converter.parse(score_path)
    events, end_time = _collect_events(score, edo=DEFAULT_EDO, bin_cents=DEFAULT_BIN_CENTS)

    explicit_params = (abs(bin_cents - DEFAULT_BIN_CENTS) > _TOL) or (edo != DEFAULT_EDO)
    active_bin_cents = DEFAULT_BIN_CENTS
    active_edo = DEFAULT_EDO
    active_preset: str | None = "12_edo"
    tuning_provenance = "default_12_edo"
    auto_detected_from_n_events: int | None = None

    if explicit_params:
        active_bin_cents = bin_cents
        active_edo = edo
        tuning_provenance = "explicit_bin_cents_edo"
        for name, preset in TUNING_PRESETS.items():
            if (
                int(preset["edo"]) == active_edo
                and abs(float(preset["bin_cents"]) - active_bin_cents) <= _TOL
            ):
                active_preset = name
                break
        else:
            active_preset = None
    elif tuning_preset is not None:
        preset = TUNING_PRESETS[tuning_preset]
        active_bin_cents = float(preset["bin_cents"])
        active_edo = int(preset["edo"])
        active_preset = tuning_preset
        tuning_provenance = "tuning_preset"
    elif auto_detect_tuning:
        detected = detect_tuning_grid(events)
        active_bin_cents = float(detected["detected_bin_cents"])
        active_edo = int(detected["detected_edo"])
        active_preset = detected.get("tuning_preset_match")
        tuning_provenance = "auto_detected"
        auto_detected_from_n_events = len(events)

    _requantize_events(events, bin_cents=active_bin_cents, edo=active_edo)
    non_grid = _non_grid_pitches(events, bin_cents=active_bin_cents)
    warnings: list[dict[str, Any]] = []
    if non_grid:
        warnings.append(
            {
                "code": "non_grid_pitches",
                "severity": "warning",
                "message": (
                    "The score contains pitches that cannot be quantised exactly "
                    "to the active tuning grid. These events have been quantised "
                    "to the nearest grid point. Consider increasing the grid "
                    "resolution (smaller bin_cents) or supplying a custom "
                    "tuning."
                ),
                "details": {
                    "n_non_grid_pitches": len(non_grid),
                    "active_bin_cents": float(active_bin_cents),
                    "active_edo": int(active_edo),
                    "sample": non_grid[:5],
                },
            }
        )

    times = _time_axis(end_time, time_step, events)
    series = _build_cardinality_series(times, events)
    result: dict[str, Any] = {
        "source_file_name": Path(str(score_path)).name,
        "time_step": float(time_step) if time_step is not None else None,
        "sampling": (
            "event_boundaries_with_uniform_grid"
            if time_step is not None
            else "event_boundaries_only"
        ),
        "duration_quarters": float(end_time),
        "event_count": len(events),
        "sample_count": len(times),
        "edo": int(active_edo),
        "pitch_class_universe": f"Z{active_edo}",
        "bin_cents": float(active_bin_cents),
        "warnings": warnings,
        "params": {
            "tuning": {
                "bin_cents": float(active_bin_cents),
                "edo": int(active_edo),
                "tuning_preset": active_preset,
                "tuning_provenance": tuning_provenance,
                "auto_detected_from_n_events": auto_detected_from_n_events,
                "non_grid_pitches_count": len(non_grid),
                "non_grid_pitches_sample": non_grid[:5],
            }
        },
        "series": series,
    }
    if debug_export_internal_path:
        result["source_file_internal_path"] = str(score_path)
    return result

def write_cardinality_csv(analysis: dict[str, Any]) -> str:
    with tempfile.NamedTemporaryFile(
        prefix="textural_dimension_cardinality_",
        suffix=".csv",
        delete=False,
    ) as tf:
        out_path = tf.name
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        tuning = analysis.get("params", {}).get("tuning", {})
        f.write(
            "# sampling: "
            f"{analysis.get('sampling', 'n/a')}, "
            f"time_step={analysis.get('time_step')}, "
            f"sample_count={analysis.get('sample_count', len(analysis.get('series', [])))}, "
            f"event_count={analysis.get('event_count', 'n/a')}; "
            f"tuning: bin_cents={tuning.get('bin_cents', analysis.get('bin_cents'))}, "
            f"edo={tuning.get('edo', analysis.get('edo'))}, "
            f"preset={tuning.get('tuning_preset')}, "
            f"provenance={tuning.get('tuning_provenance')}\n"
        )
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
