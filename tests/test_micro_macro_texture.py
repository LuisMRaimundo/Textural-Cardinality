from __future__ import annotations

from collections import Counter

from music21.note import Note
from music21.pitch import Pitch
from music21.stream import Part, Score

from textural_dimension.analysis import (
    REFERENCE_UNIVERSE_12TET,
    REFERENCE_UNIVERSE_QUARTER_TONE,
    _build_cardinality_series,
    _collect_events,
    _time_axis,
    meso_pole_cardinality,
    micro_macro_normalized,
    micro_meso_macro_normalized,
    micro_macro_texture_params,
    reference_pitch_universe_size,
)


def test_reference_universe_sizes() -> None:
    assert reference_pitch_universe_size(100.0) == REFERENCE_UNIVERSE_12TET
    assert reference_pitch_universe_size(50.0) == REFERENCE_UNIVERSE_QUARTER_TONE
    params_12 = micro_macro_texture_params(100.0)
    params_24 = micro_macro_texture_params(50.0)
    assert params_12["macro_pole_cardinality"] == 88
    assert params_24["macro_pole_cardinality"] == 175
    assert params_12["meso_pole_cardinality"] == meso_pole_cardinality(88)
    assert params_24["meso_pole_cardinality"] == meso_pole_cardinality(175)
    assert params_12["meso_pole_normalized"] == 0.5


def test_micro_meso_macro_normalized_anchors_three_poles() -> None:
    assert micro_meso_macro_normalized(1, 88) == 0.0
    assert micro_meso_macro_normalized(88, 88) == 1.0
    assert meso_pole_cardinality(88) == 44.5
    assert micro_meso_macro_normalized(44, 88) == round(43 / 87, 6)
    assert micro_meso_macro_normalized(45, 88) == round(44 / 87, 6)
    assert micro_meso_macro_normalized(1, 175) == 0.0
    assert micro_meso_macro_normalized(175, 175) == 1.0
    assert meso_pole_cardinality(175) == 88.0


def test_micro_macro_normalized_uses_universe_as_macro_pole() -> None:
    assert micro_macro_normalized(1, 88) == round(1 / 88, 6)
    assert micro_macro_normalized(88, 88) == 1.0
    assert micro_macro_normalized(2, 175) == round(2 / 175, 6)


def test_pitch_outside_a0_c8_excluded_from_micro_macro_count() -> None:
    score = Score()
    part = Part()
    in_range = Note("C4", quarterLength=1.0)
    out_of_range = Note(quarterLength=1.0)
    out_of_range.pitch = Pitch(ps=120.0)  # above C8
    part.insert(0.0, in_range)
    part.insert(0.0, out_of_range)
    score.insert(0.0, part)

    events, end_time = _collect_events(score)
    times = _time_axis(end_time, 1.0, events)
    series = _build_cardinality_series(times, events, reference_universe_size=REFERENCE_UNIVERSE_12TET)

    row = series[0]
    assert row["vertical_note_count"] == 2
    assert row["vertical_unique_pitch_count"] == 2
    assert row["micro_macro_pitch_cardinality"] == 1
    assert row["micro_macro_normalized"] == micro_macro_normalized(1, REFERENCE_UNIVERSE_12TET)
    assert row["micro_meso_macro_normalized"] == micro_meso_macro_normalized(1, REFERENCE_UNIVERSE_12TET)


def test_chord_in_reference_register_counts_all_distinct_micro_macro_pitches() -> None:
    score = Score()
    part = Part()
    for pitch_name in ("C4", "E4", "G4"):
        part.insert(0.0, Note(pitch_name, quarterLength=1.0))
    score.insert(0.0, part)

    events, end_time = _collect_events(score)
    times = _time_axis(end_time, 1.0, events)
    series = _build_cardinality_series(times, events, reference_universe_size=REFERENCE_UNIVERSE_12TET)

    assert series[0]["micro_macro_pitch_cardinality"] == 3
    assert series[0]["micro_macro_normalized"] == micro_macro_normalized(3, REFERENCE_UNIVERSE_12TET)
    assert series[0]["micro_meso_macro_normalized"] == micro_meso_macro_normalized(
        3, REFERENCE_UNIVERSE_12TET
    )


def test_quarter_tone_grid_uses_175_position_universe() -> None:
    score = Score()
    part = Part()
    n1 = Note(quarterLength=1.0)
    n1.pitch = Pitch(ps=60.0)
    n2 = Note(quarterLength=1.0)
    n2.pitch = Pitch(ps=60.5)
    part.insert(0.0, n1)
    part.insert(0.0, n2)
    score.insert(0.0, part)

    events, end_time = _collect_events(score, edo=24, bin_cents=50)
    times = _time_axis(end_time, 1.0, events)
    series = _build_cardinality_series(
        times,
        events,
        reference_universe_size=REFERENCE_UNIVERSE_QUARTER_TONE,
    )

    assert series[0]["micro_macro_pitch_cardinality"] == 2
    assert series[0]["micro_macro_normalized"] == micro_macro_normalized(2, REFERENCE_UNIVERSE_QUARTER_TONE)
    assert series[0]["micro_meso_macro_normalized"] == micro_meso_macro_normalized(
        2, REFERENCE_UNIVERSE_QUARTER_TONE
    )


def test_sweep_ref_units_match_naive_counter() -> None:
    score = Score()
    part = Part()
    part.insert(0.0, Note("C4", quarterLength=2.0))
    n2 = Note("E4", quarterLength=1.0)
    n2.offset = 1.0
    part.insert(1.0, n2)
    score.insert(0.0, part)

    events, end_time = _collect_events(score)
    times = _time_axis(end_time, 1.0, events)
    sweep = _build_cardinality_series(times, events, reference_universe_size=REFERENCE_UNIVERSE_12TET)

    for t, row in zip(times, sweep):
        ref_counter: Counter[int] = Counter()
        for ev in events:
            if ev["offset"] <= t < ev["end"] + 1e-9:
                ref_counter.update(ev.get("ref_units", []))
        assert row["micro_macro_pitch_cardinality"] == len(ref_counter)
        assert row["micro_macro_normalized"] == micro_macro_normalized(len(ref_counter), REFERENCE_UNIVERSE_12TET)
        assert row["micro_meso_macro_normalized"] == micro_meso_macro_normalized(
            len(ref_counter), REFERENCE_UNIVERSE_12TET
        )
