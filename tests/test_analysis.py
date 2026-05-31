from __future__ import annotations

from music21.note import Note
from music21.pitch import Pitch
from music21.stream import Measure, Part, Score

from textural_dimension.analysis import _build_cardinality_series, _collect_events, _time_axis
from textural_dimension.cardinality import vertical_cardinality_for_notes


def test_collect_events_and_series_basics() -> None:
    score = Score()
    part = Part()
    n1 = Note("C4", quarterLength=2.0)
    n2 = Note("E4", quarterLength=1.0)
    n2.offset = 1.0
    part.insert(0.0, n1)
    part.insert(1.0, n2)
    score.insert(0.0, part)

    events, end_time = _collect_events(score)
    assert len(events) == 2
    assert end_time == 2.0

    times = _time_axis(end_time, 1.0, events)
    assert times == [0.0, 1.0, 2.0]

    # t=1.0 has C4 and E4 active together.
    active = []
    for ev in events:
        if ev["offset"] <= 1.0 < ev["end"] + 1e-9:
            active.extend(ev["notes"])
    card = vertical_cardinality_for_notes(active)
    assert card["vertical_note_count"] == 2
    assert card["vertical_unique_pitch_count"] == 2
    assert card["vertical_pitch_class_cardinality"] == 2


def test_collect_events_uses_global_hierarchy_offsets() -> None:
    score = Score()
    part = Part()
    m1 = Measure(number=1)
    m2 = Measure(number=2)
    m1.insert(0.0, Note("C4", quarterLength=1.0))
    m2.insert(0.0, Note("D4", quarterLength=1.0))
    part.insert(0.0, m1)
    part.insert(1.0, m2)
    score.insert(0.0, part)

    events, end_time = _collect_events(score)
    assert len(events) == 2
    assert end_time == 2.0
    offsets = sorted(float(ev["offset"]) for ev in events)
    assert offsets == [0.0, 1.0]


def test_sweepline_series_matches_naive_scan() -> None:
    score = Score()
    part = Part()
    n1 = Note("C4", quarterLength=2.0)
    n2 = Note("E4", quarterLength=1.0)
    n2.offset = 1.0
    n3 = Note("G4", quarterLength=1.0)
    n3.offset = 1.5
    part.insert(0.0, n1)
    part.insert(1.0, n2)
    part.insert(1.5, n3)
    score.insert(0.0, part)

    events, end_time = _collect_events(score)
    times = _time_axis(end_time, 0.5, events)

    sweep = _build_cardinality_series(times, events)

    naive = []
    for t in times:
        active_notes = []
        for ev in events:
            if ev["offset"] <= t < ev["end"] + 1e-9:
                active_notes.extend(ev["notes"])
        card = vertical_cardinality_for_notes(active_notes, bin_cents=100, edo=12)
        naive.append(
            {
                "time_quarters": t,
                "vertical_note_count": card["vertical_note_count"],
                "vertical_unique_pitch_count": card["vertical_unique_pitch_count"],
                "vertical_pitch_class_cardinality": card["vertical_pitch_class_cardinality"],
            }
        )
    assert sweep == naive


def test_collect_events_supports_24_edo_pc_cardinality() -> None:
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
    series = _build_cardinality_series(times, events)

    assert series[0]["vertical_note_count"] == 2
    assert series[0]["vertical_pitch_class_cardinality"] == 2


def test_collect_events_supports_48_edo_pc_cardinality() -> None:
    score = Score()
    part = Part()

    for ps in [60.0, 60.25, 60.5]:
        n = Note(quarterLength=1.0)
        n.pitch = Pitch(ps=ps)
        part.insert(0.0, n)

    score.insert(0.0, part)

    events, end_time = _collect_events(score, edo=48, bin_cents=25)
    times = _time_axis(end_time, 1.0, events)
    series = _build_cardinality_series(times, events)

    assert series[0]["vertical_note_count"] == 3
    assert series[0]["vertical_pitch_class_cardinality"] == 3


def test_time_axis_includes_event_boundaries() -> None:
    score = Score()
    part = Part()
    part.insert(0.0, Note("C4", quarterLength=4.0))
    grace = Note("E4", quarterLength=0.01)
    grace.offset = 1.01
    part.insert(1.01, grace)
    score.insert(0.0, part)

    events, end_time = _collect_events(score)
    times = _time_axis(end_time, 1.0, events)

    assert 1.01 in times
    assert 1.02 in times


def test_sub_step_grace_note_captured_on_event_axis() -> None:
    score = Score()
    part = Part()
    part.insert(0.0, Note("C4", quarterLength=4.0))
    grace = Note("E4", quarterLength=0.01)
    grace.offset = 1.01
    part.insert(1.01, grace)
    score.insert(0.0, part)

    events, end_time = _collect_events(score)

    grid_only = _time_axis(end_time, 1.0, events=None)
    event_axis = _time_axis(end_time, 1.0, events=events)

    grid_series = _build_cardinality_series(grid_only, events)
    event_series = _build_cardinality_series(event_axis, events)

    assert max(r["vertical_note_count"] for r in grid_series) == 1
    assert max(r["vertical_note_count"] for r in event_series) == 2

    peak_rows = [r for r in event_series if r["vertical_note_count"] == 2]
    assert any(abs(float(r["time_quarters"]) - 1.01) < 1e-6 for r in peak_rows)