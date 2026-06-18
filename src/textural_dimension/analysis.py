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

from textural_dimension.pitch_grid import (
    NoteTuple,
    TUNING_PRESETS,
    _STEP_TO_SEMITONE,
    _midi_from_note_tuple,
    _nearest_int,
    _pc_class,
    _pitch_unit,
    validate_edo,
)

_EPS = 1e-9
_TOL = 1e-6
DEFAULT_BIN_CENTS = 100.0
DEFAULT_EDO = 12
REFERENCE_REGISTER_LOW = "A0"
REFERENCE_REGISTER_HIGH = "C8"
REFERENCE_PS_LOW = 21.0  # A0 in pitch-space (midi 21)
REFERENCE_PS_HIGH = 108.0  # C8 in pitch-space (midi 108)
REFERENCE_UNIVERSE_12TET = 88
REFERENCE_UNIVERSE_QUARTER_TONE = 175
MICRO_POLE_CARDINALITY = 1


def validate_bin_cents(bin_cents: float) -> float:
    bin_cents = float(bin_cents)
    if bin_cents <= 0:
        raise ValueError("bin_cents must be > 0")
    return bin_cents


def _pitch_to_note_tuple(p: Pitch) -> NoteTuple | None:
    if p.octave is None:
        return None
    step = str(p.step).upper()
    octave = int(p.octave)
    base_ps = 12.0 * (octave + 1) + _STEP_TO_SEMITONE[step]
    alter = float(p.ps) - base_ps
    return (step, alter, octave)


def _ps_in_reference_register(ps: float, tol: float = _TOL) -> bool:
    return (REFERENCE_PS_LOW - tol) <= float(ps) <= (REFERENCE_PS_HIGH + tol)


def _note_in_reference_register(note: NoteTuple, tol: float = _TOL) -> bool:
    return _ps_in_reference_register(_midi_from_note_tuple(note), tol=tol)


def reference_pitch_universe_size(bin_cents: float) -> int:
    """Return the closed A0–C8 pitch-position count for the active grid."""
    bin_cents = validate_bin_cents(bin_cents)
    if abs(bin_cents - DEFAULT_BIN_CENTS) <= _TOL:
        return REFERENCE_UNIVERSE_12TET
    if abs(bin_cents - 50.0) <= _TOL:
        return REFERENCE_UNIVERSE_QUARTER_TONE
    span_cents = (REFERENCE_PS_HIGH - REFERENCE_PS_LOW) * 100.0
    return int(round(span_cents / bin_cents)) + 1


def micro_macro_normalized(cardinality: int, universe_size: int) -> float:
    if universe_size <= 0:
        return 0.0
    return round(min(1.0, max(0.0, float(cardinality) / float(universe_size))), 6)


def meso_pole_cardinality(universe_size: int) -> float:
    """Arithmetic centre between micro (1) and macro (universe_size) poles."""
    universe_size = int(universe_size)
    if universe_size <= 0:
        return 0.0
    return (1.0 + float(universe_size)) / 2.0


def micro_meso_macro_normalized(cardinality: int, universe_size: int) -> float:
    """Map micro→0, meso centre→0.5, macro→1 on the closed A0–C8 cardinality span."""
    universe_size = int(universe_size)
    if universe_size <= 1:
        return 0.0 if int(cardinality) <= 1 else 1.0
    span = float(universe_size - 1)
    return round(min(1.0, max(0.0, (float(cardinality) - 1.0) / span)), 6)


def _ref_pitch_units(notes: list[NoteTuple], *, bin_cents: float) -> list[int]:
    units: list[int] = []
    for note in notes:
        if _note_in_reference_register(note):
            units.append(_pitch_unit(note, bin_cents=bin_cents))
    return units


def micro_macro_texture_params(bin_cents: float) -> dict[str, Any]:
    universe_size = reference_pitch_universe_size(bin_cents)
    meso_card = meso_pole_cardinality(universe_size)
    return {
        "reference_register": f"{REFERENCE_REGISTER_LOW}-{REFERENCE_REGISTER_HIGH}",
        "reference_ps_low": REFERENCE_PS_LOW,
        "reference_ps_high": REFERENCE_PS_HIGH,
        "reference_pitch_universe_size": universe_size,
        "micro_pole_cardinality": MICRO_POLE_CARDINALITY,
        "meso_pole_cardinality": meso_card,
        "macro_pole_cardinality": universe_size,
        "texture_scale": "micro_meso_macro",
        "micro_pole_normalized": 0.0,
        "meso_pole_normalized": 0.5,
        "macro_pole_normalized": 1.0,
    }


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
        ev["ref_units"] = _ref_pitch_units(pitches, bin_cents=bin_cents)


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
                "ref_units": _ref_pitch_units(pitches, bin_cents=bin_cents),
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


def _build_cardinality_series(
    times: list[float],
    events: list[dict[str, Any]],
    *,
    reference_universe_size: int,
) -> list[dict[str, Any]]:
    if not times:
        return []

    starts = sorted(events, key=lambda ev: (float(ev["offset"]), float(ev["end"])))
    ends = sorted(events, key=lambda ev: (float(ev["end"]), float(ev["offset"])))
    si = 0
    ei = 0

    active_note_count = 0
    active_units: Counter[int] = Counter()
    active_pcs: Counter[int] = Counter()
    active_ref_units: Counter[int] = Counter()

    series: list[dict[str, Any]] = []
    for t in times:
        # Half-open activity semantics [onset, offset): a note is inactive at t == end,
        # so it is removed once end <= t (no release-inclusive overlap spike at shared
        # boundaries). Zero-duration events span an empty half-open interval and therefore
        # contribute no vertical cardinality.
        while ei < len(ends) and float(ends[ei]["end"]) <= t + _EPS:
            ev = ends[ei]
            ei += 1
            if (float(ev["end"]) - float(ev["offset"])) <= _EPS:
                continue
            active_note_count -= len(ev["notes"])
            for unit in ev["units"]:
                active_units[unit] -= 1
                if active_units[unit] <= 0:
                    del active_units[unit]
            for pc in ev["pcs"]:
                active_pcs[pc] -= 1
                if active_pcs[pc] <= 0:
                    del active_pcs[pc]
            for unit in ev.get("ref_units", []):
                active_ref_units[unit] -= 1
                if active_ref_units[unit] <= 0:
                    del active_ref_units[unit]

        while si < len(starts) and float(starts[si]["offset"]) <= t + _EPS:
            ev = starts[si]
            si += 1
            if (float(ev["end"]) - float(ev["offset"])) <= _EPS:
                continue
            active_note_count += len(ev["notes"])
            active_units.update(ev["units"])
            active_pcs.update(ev["pcs"])
            active_ref_units.update(ev.get("ref_units", []))

        mm_card = len(active_ref_units)
        series.append(
            {
                "time_quarters": t,
                "vertical_note_count": int(active_note_count),
                "vertical_unique_pitch_count": int(len(active_units)),
                "vertical_pitch_class_cardinality": int(len(active_pcs)),
                "micro_macro_pitch_cardinality": int(mm_card),
                "micro_macro_normalized": micro_macro_normalized(mm_card, reference_universe_size),
                "micro_meso_macro_normalized": micro_meso_macro_normalized(
                    mm_card, reference_universe_size
                ),
            }
        )
    return series


def _merge_tied_notes(score: Score) -> tuple[Score, bool]:
    """
    Merge tied note chains into single sustained events before event extraction.

    A tie start + continuation(s) becomes one event spanning the union duration via
    music21 ``stripTies`` (``matchByPitch=True`` so chord-internal and pitch-matched ties
    merge while untied members remain separate). Rearticulated (untied) notes are left
    as distinct events. On any music21 failure the original score is returned with
    ``ok=False`` so analysis can still proceed (and emit a ``tie_merge_failed`` warning).
    """
    try:
        merged = score.stripTies(inPlace=False, matchByPitch=True)
        if merged is None:
            return score, False
        return merged, True
    except Exception:
        return score, False


def analyze_vertical_cardinality(
    score_path: str,
    *,
    time_step: float | None = 0.25,
    edo: int = DEFAULT_EDO,
    bin_cents: float = DEFAULT_BIN_CENTS,
    auto_detect_tuning: bool = False,
    tuning_preset: str | None = None,
    merge_ties: bool = True,
    debug_export_internal_path: bool = False,
) -> dict[str, Any]:
    edo = validate_edo(edo)
    bin_cents = validate_bin_cents(bin_cents)
    if tuning_preset is not None and tuning_preset not in TUNING_PRESETS:
        raise ValueError(f"Unknown tuning_preset: {tuning_preset}")

    score = converter.parse(score_path)
    tie_merge_ok = True
    if merge_ties:
        score, tie_merge_ok = _merge_tied_notes(score)
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
    if merge_ties and not tie_merge_ok:
        warnings.append(
            {
                "code": "tie_merge_failed",
                "severity": "warning",
                "message": (
                    "music21 stripTies could not merge tied notes for this score; "
                    "tied continuations may be counted as separate events."
                ),
                "details": {},
            }
        )
    n_zero_duration = sum(
        1 for ev in events if (float(ev["end"]) - float(ev["offset"])) <= _EPS
    )
    if n_zero_duration:
        warnings.append(
            {
                "code": "zero_duration_events",
                "severity": "info",
                "message": (
                    "Zero-duration events (e.g. notated grace notes with no duration) "
                    "contribute no vertical cardinality under half-open [onset, offset) "
                    "activity semantics."
                ),
                "details": {"n_zero_duration_events": int(n_zero_duration)},
            }
        )

    times = _time_axis(end_time, time_step, events)
    ref_universe_size = reference_pitch_universe_size(active_bin_cents)
    series = _build_cardinality_series(times, events, reference_universe_size=ref_universe_size)
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
            "temporal_semantics": {
                "activity_interval": "half_open_onset_offset",
                "active_predicate": "onset <= t < offset",
                "tie_handling": "merge_tied_notes" if merge_ties else "as_imported",
                "tie_merge_applied": bool(merge_ties and tie_merge_ok),
                "zero_duration_policy": "ignored_no_contribution",
            },
            "micro_macro_texture": micro_macro_texture_params(active_bin_cents),
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
        mm = analysis.get("params", {}).get("micro_macro_texture", {})
        f.write(
            "# sampling: "
            f"{analysis.get('sampling', 'n/a')}, "
            f"time_step={analysis.get('time_step')}, "
            f"sample_count={analysis.get('sample_count', len(analysis.get('series', [])))}, "
            f"event_count={analysis.get('event_count', 'n/a')}; "
            f"micro_macro: register={mm.get('reference_register', 'A0-C8')}, "
            f"universe_size={mm.get('reference_pitch_universe_size', 'n/a')}, "
            f"poles=micro:{mm.get('micro_pole_cardinality', 1)}/"
            f"meso:{mm.get('meso_pole_cardinality', 'n/a')}/"
            f"macro:{mm.get('macro_pole_cardinality', 'n/a')}; "
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
                "micro_macro_pitch_cardinality",
                "micro_macro_normalized",
                "micro_meso_macro_normalized",
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
