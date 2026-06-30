"""Phase 0 parity tests: analysis.py pitch primitives vs iav/vertical_cardinality.py."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from music21.note import Note
from music21.pitch import Pitch
from music21.stream import Part, Score

import iav.vertical_cardinality as iav_vc
import textural_cardinality.analysis as analysis
from textural_cardinality.analysis import (
    REFERENCE_UNIVERSE_12TET,
    REFERENCE_UNIVERSE_QUARTER_TONE,
    TUNING_PRESETS,
    _build_cardinality_series,
    _collect_events,
    _midi_from_note_tuple,
    _pc_class,
    _pitch_unit,
    _time_axis,
    analyze_vertical_cardinality,
    micro_macro_normalized,
    micro_meso_macro_normalized,
    validate_edo,
)
from iav.vertical_cardinality import (
    NoteTuple,
    vertical_cardinality_for_notes,
)

CORPUS_DIR = Path(__file__).resolve().parent / "fixtures" / "regression_corpus"
CORPUS_FIXTURES = tuple(
    path.stem for path in sorted(CORPUS_DIR.glob("*.musicxml"))
)

MAX_CARDINALITY_FIELDS = (
    "max_vertical_note_count",
    "max_vertical_unique_pitch_count",
    "max_vertical_pitch_class_cardinality",
)


def _c_tuple(ps: float, *, octave: int = 4) -> NoteTuple:
    """Build a C-step NoteTuple whose pitch-space equals ``ps``."""
    base_ps = 12.0 * (octave + 1)
    return ("C", float(ps - base_ps), octave)


def _analysis_slice_cardinality(
    notes: Sequence[NoteTuple],
    *,
    bin_cents: float,
    edo: int,
) -> dict[str, int]:
    return {
        "vertical_note_count": len(notes),
        "vertical_unique_pitch_count": len({_pitch_unit(n, bin_cents=bin_cents) for n in notes}),
        "vertical_pitch_class_cardinality": len({_pc_class(n, edo=edo) for n in notes}),
    }


# --------------------------------------------------------------------------------------
# 1. Constant parity
# --------------------------------------------------------------------------------------
def test_step_to_semitone_parity() -> None:
    assert analysis._STEP_TO_SEMITONE == iav_vc._STEP_TO_SEMITONE


def test_tuning_presets_parity() -> None:
    assert analysis.TUNING_PRESETS == iav_vc.TUNING_PRESETS


# --------------------------------------------------------------------------------------
# 2. validate_edo parity
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("edo", [12, 19, 24, 31, 48, 53, 72])
def test_validate_edo_accepts_same_values(edo: int) -> None:
    assert validate_edo(edo) == iav_vc.validate_edo(edo) == edo


@pytest.mark.parametrize(
    "invalid",
    [
        pytest.param(0, id="zero"),
        pytest.param(-12, id="negative"),
        pytest.param(12.5, id="float-truncates-to-twelve"),
        pytest.param("24", id="numeric-string"),
        pytest.param(None, id="none"),
    ],
)
def test_validate_edo_rejects_or_coerces_consistently(invalid: Any) -> None:
    if invalid in (0, -12, None):
        with pytest.raises((ValueError, TypeError)) as analysis_exc:
            validate_edo(invalid)  # type: ignore[arg-type]
        with pytest.raises((ValueError, TypeError)) as iav_exc:
            iav_vc.validate_edo(invalid)  # type: ignore[arg-type]
        assert type(analysis_exc.value) is type(iav_exc.value)
    else:
        assert validate_edo(invalid) == iav_vc.validate_edo(invalid)  # type: ignore[arg-type]


# --------------------------------------------------------------------------------------
# 3. MIDI conversion parity
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "note",
    [
        ("C", 0.0, 4),
        ("C", 1.0, 4),
        ("D", -1.0, 4),
        ("F", 1.0, 3),
        ("B", -1.0, 5),
        ("C", 0.5, 4),
        ("C", 1.25, 4),
    ],
    ids=[
        "C4",
        "C#4",
        "Db4",
        "F#3",
        "Bb5",
        "quarter-tone-up",
        "quarter-tone-between-cs-and-d",
    ],
)
def test_midi_from_note_tuple_parity(note: NoteTuple) -> None:
    assert _midi_from_note_tuple(note) == iav_vc._midi_from_note_tuple(note)


# --------------------------------------------------------------------------------------
# 4. Pitch-unit parity
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("ps", [60.0, 60.5, 61.0, 61.25, 61.75, 72.0, 36.0])
@pytest.mark.parametrize("bin_cents", [100.0, 50.0, 25.0, 1200.0 / 31.0])
def test_pitch_unit_parity(ps: float, bin_cents: float) -> None:
    octave = 2 if ps <= 40.0 else (5 if ps >= 72.0 else 4)
    note = _c_tuple(ps, octave=octave)
    assert _pitch_unit(note, bin_cents=bin_cents) == iav_vc._pitch_unit(note, bin_cents=bin_cents)


# --------------------------------------------------------------------------------------
# 5. Pitch-class parity
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("ps", [60.0, 60.49, 60.5, 60.51, 61.0, 71.99, 72.0])
@pytest.mark.parametrize("edo", [12, 19, 24, 31, 48, 53, 72])
def test_pc_class_parity(ps: float, edo: int) -> None:
    octave = 5 if ps >= 72.0 else 4
    note = _c_tuple(ps, octave=octave)
    assert _pc_class(note, edo=edo) == iav_vc._pc_class(note, edo=edo)


# --------------------------------------------------------------------------------------
# 6. Slice cardinality parity
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "notes,bin_cents,edo,case_id",
    [
        ([("C", 0.0, 4)], 100.0, 12, "monophony"),
        ([("C", 0.0, 4), ("C", 0.0, 4)], 100.0, 12, "unison-doubling"),
        ([("C", 0.0, 4), ("C", 0.0, 5)], 100.0, 12, "octave-doubling"),
        ([("C", 0.0, 4), ("E", 0.0, 4)], 100.0, 12, "dyad"),
        ([("C", 0.0, 4), ("E", 0.0, 4), ("G", 0.0, 4)], 100.0, 12, "triad"),
        (
            [("C", 0.0, 4), ("C", 1.0, 4), ("D", 0.0, 4), ("D", 1.0, 4), ("E", 0.0, 4)],
            100.0,
            12,
            "chromatic-cluster",
        ),
        ([("C", 1.0, 4), ("D", -1.0, 4)], 100.0, 12, "enharmonic-cs-db"),
        ([("C", 0.0, 4), ("C", 0.5, 4)], 50.0, 24, "quarter-tone-dyad"),
    ],
)
def test_slice_cardinality_parity(
    notes: list[NoteTuple],
    bin_cents: float,
    edo: int,
    case_id: str,
) -> None:
    del case_id
    iav_card = vertical_cardinality_for_notes(notes, bin_cents=bin_cents, edo=edo)
    analysis_card = _analysis_slice_cardinality(notes, bin_cents=bin_cents, edo=edo)
    assert analysis_card == iav_card


# --------------------------------------------------------------------------------------
# 7. Sweep-line naive parity extension (beyond existing 12-EDO test)
# --------------------------------------------------------------------------------------
def _overlapping_score_quarter_tone() -> Score:
    score = Score()
    part = Part()
    n1 = Note(quarterLength=2.0)
    n1.pitch = Pitch(ps=60.0)
    n2 = Note(quarterLength=1.0)
    n2.pitch = Pitch(ps=60.5)
    n2.offset = 1.0
    part.insert(0.0, n1)
    part.insert(1.0, n2)
    score.insert(0.0, part)
    return score


def _overlapping_score_eighth_tone() -> Score:
    score = Score()
    part = Part()
    for ps in [60.0, 60.25, 60.5]:
        note = Note(quarterLength=1.0)
        note.pitch = Pitch(ps=ps)
        part.insert(0.0, note)
    n_last = Note(quarterLength=0.5)
    n_last.pitch = Pitch(ps=61.0)
    n_last.offset = 0.5
    part.insert(0.5, n_last)
    score.insert(0.0, part)
    return score


def _overlapping_score_31_edo() -> Score:
    score = Score()
    part = Part()
    part.insert(0.0, Note("C4", quarterLength=2.0))
    part.insert(1.0, Note("E4", quarterLength=1.0))
    score.insert(0.0, part)
    return score


def _assert_sweep_matches_naive_iav_scan(
    score: Score,
    *,
    edo: int,
    bin_cents: float,
    reference_universe_size: int,
) -> None:
    events, end_time = _collect_events(score, edo=edo, bin_cents=bin_cents)
    times = _time_axis(end_time, 0.5, events)
    sweep = _build_cardinality_series(times, events, reference_universe_size=reference_universe_size)

    naive = []
    for t in times:
        active_notes: list[NoteTuple] = []
        ref_counter: Counter[int] = Counter()
        for ev in events:
            if ev["offset"] <= t < ev["end"]:
                active_notes.extend(ev["notes"])
                ref_counter.update(ev.get("ref_units", []))
        card = vertical_cardinality_for_notes(active_notes, bin_cents=bin_cents, edo=edo)
        mm_card = len(ref_counter)
        naive.append(
            {
                "time_quarters": t,
                "vertical_note_count": card["vertical_note_count"],
                "vertical_unique_pitch_count": card["vertical_unique_pitch_count"],
                "vertical_pitch_class_cardinality": card["vertical_pitch_class_cardinality"],
                "micro_macro_pitch_cardinality": mm_card,
                "micro_macro_normalized": micro_macro_normalized(mm_card, reference_universe_size),
                "micro_meso_macro_normalized": micro_meso_macro_normalized(
                    mm_card, reference_universe_size
                ),
            }
        )
    assert sweep == naive


@pytest.mark.parametrize(
    "score_factory,edo,bin_cents,universe,case_id",
    [
        (_overlapping_score_quarter_tone, 24, 50.0, REFERENCE_UNIVERSE_QUARTER_TONE, "24-edo"),
        (_overlapping_score_eighth_tone, 48, 25.0, REFERENCE_UNIVERSE_QUARTER_TONE, "48-edo"),
        (
            _overlapping_score_31_edo,
            31,
            TUNING_PRESETS["31_edo"]["bin_cents"],
            int(round((108.0 - 21.0) * 100.0 / TUNING_PRESETS["31_edo"]["bin_cents"])) + 1,
            "31-edo",
        ),
    ],
)
def test_sweepline_naive_parity_extended(
    score_factory,
    edo: int,
    bin_cents: float,
    universe: int,
    case_id: str,
) -> None:
    del case_id
    _assert_sweep_matches_naive_iav_scan(
        score_factory(),
        edo=edo,
        bin_cents=bin_cents,
        reference_universe_size=universe,
    )


# --------------------------------------------------------------------------------------
# 8. Event precompute parity
# --------------------------------------------------------------------------------------
def test_event_precompute_units_and_pcs_match_iav_primitives() -> None:
    score = Score()
    part = Part()
    part.insert(0.0, Note("C4", quarterLength=2.0))
    n2 = Note(quarterLength=1.0)
    n2.pitch = Pitch(ps=60.5)
    n2.offset = 1.0
    part.insert(1.0, n2)
    part.insert(0.0, Note("E4", quarterLength=1.5))
    score.insert(0.0, part)

    for edo, bin_cents in (
        (12, 100.0),
        (24, 50.0),
        (31, TUNING_PRESETS["31_edo"]["bin_cents"]),
    ):
        events, _ = _collect_events(score, edo=edo, bin_cents=bin_cents)
        for ev in events:
            notes = ev["notes"]
            expected_units = [iav_vc._pitch_unit(n, bin_cents=bin_cents) for n in notes]
            expected_pcs = [iav_vc._pc_class(n, edo=edo) for n in notes]
            assert ev["units"] == expected_units
            assert ev["pcs"] == expected_pcs
            assert ev["units"] == [_pitch_unit(n, bin_cents=bin_cents) for n in notes]
            assert ev["pcs"] == [_pc_class(n, edo=edo) for n in notes]


# --------------------------------------------------------------------------------------
# 9. Regression-corpus max-cardinality guard (lightweight)
# --------------------------------------------------------------------------------------
def _analysis_kwargs_for_fixture(name: str) -> dict[str, Any]:
    expected_path = CORPUS_DIR / "expected" / f"{name}.json"
    options = json.loads(expected_path.read_text(encoding="utf-8")).get("analysis_options", {})
    kwargs: dict[str, Any] = {"time_step": None}
    if preset := options.get("tuning_preset"):
        kwargs["tuning_preset"] = preset
    return kwargs


@pytest.mark.parametrize("fixture_name", CORPUS_FIXTURES)
def test_regression_corpus_max_cardinality_guard(fixture_name: str) -> None:
    expected = json.loads(
        (CORPUS_DIR / "expected" / f"{fixture_name}.json").read_text(encoding="utf-8")
    )
    analysis_result = analyze_vertical_cardinality(
        str(CORPUS_DIR / f"{fixture_name}.musicxml"),
        **_analysis_kwargs_for_fixture(fixture_name),
    )
    series = analysis_result["series"]
    assert max(row["vertical_note_count"] for row in series) == expected["max_vertical_note_count"]
    assert (
        max(row["vertical_unique_pitch_count"] for row in series)
        == expected["max_vertical_unique_pitch_count"]
    )
    assert (
        max(row["vertical_pitch_class_cardinality"] for row in series)
        == expected["max_vertical_pitch_class_cardinality"]
    )
