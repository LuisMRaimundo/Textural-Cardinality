"""Phase 2 temporal-semantics contract.

Covers the two adopted scientific decisions:

A. Tied sustained notes are merged into single sustained events before extraction.
B. Vertical activity uses half-open intervals ``[onset, offset)`` (a note is inactive
   at ``t == offset``; coincident end/onset are not double-counted).

Plus the explicit zero-duration policy: zero-duration events contribute no cardinality.
"""

from __future__ import annotations

from pathlib import Path
import tempfile

from music21.note import Note
from music21.stream import Measure, Part, Score
from music21.tie import Tie

from textural_dimension.analysis import (
    REFERENCE_UNIVERSE_12TET,
    _build_cardinality_series,
    _collect_events,
    _merge_tied_notes,
    _pc_class,
    _pitch_unit,
    _ref_pitch_units,
    _time_axis,
    analyze_vertical_cardinality,
)


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
def _sequential_measures_score(specs: list[tuple[str, float, str | None]]) -> Score:
    """Build a single-part score, one note per measure, laid out sequentially in time."""
    part = Part()
    offset = 0.0
    for i, (pitch, dur, tie_type) in enumerate(specs):
        measure = Measure(number=i + 1)
        note = Note(pitch, quarterLength=dur)
        if tie_type is not None:
            note.tie = Tie(tie_type)
        measure.insert(0.0, note)
        part.insert(offset, measure)
        offset += dur
    score = Score()
    score.insert(0.0, part)
    return score


def _series_by_time(score: Score, time_step: float = 1.0) -> dict[float, dict]:
    events, end_time = _collect_events(score)
    times = _time_axis(end_time, time_step, events)
    series = _build_cardinality_series(times, events, reference_universe_size=REFERENCE_UNIVERSE_12TET)
    return {round(float(r["time_quarters"]), 6): r for r in series}


# --------------------------------------------------------------------------------------
# A. Tie handling
# --------------------------------------------------------------------------------------
def test_two_tied_half_notes_across_barline_merge_to_one_event() -> None:
    score = _sequential_measures_score([("C4", 2.0, "start"), ("C4", 2.0, "stop")])
    raw_events, _ = _collect_events(score)
    merged_score, ok = _merge_tied_notes(score)
    merged_events, end_time = _collect_events(merged_score)

    assert ok is True
    assert len(raw_events) == 2  # two notated note objects before merge
    assert len(merged_events) == 1  # one sustained event after merge
    assert round(float(merged_events[0]["offset"]), 6) == 0.0
    assert round(float(merged_events[0]["end"]), 6) == 4.0


def test_three_segment_tie_chain_merges_to_one_event() -> None:
    score = _sequential_measures_score(
        [("C4", 2.0, "start"), ("C4", 2.0, "continue"), ("C4", 2.0, "stop")]
    )
    merged_score, ok = _merge_tied_notes(score)
    merged_events, _ = _collect_events(merged_score)

    assert ok is True
    assert len(merged_events) == 1
    assert round(float(merged_events[0]["end"]), 6) == 6.0


def test_untied_rearticulations_remain_separate_events() -> None:
    score = _sequential_measures_score([("C4", 1.0, None), ("C4", 1.0, None)])
    merged_score, ok = _merge_tied_notes(score)
    merged_events, _ = _collect_events(merged_score)

    assert ok is True
    assert len(merged_events) == 2  # rearticulation is NOT a tie -> stays distinct


def test_partial_tie_merges_only_tied_member() -> None:
    # One tied member (C4 across the barline) + one untied member (E4) at the same onset.
    part = Part()
    m1 = Measure(number=1)
    c1 = Note("C4", quarterLength=2.0)
    c1.tie = Tie("start")
    e1 = Note("E4", quarterLength=2.0)  # untied
    m1.insert(0.0, c1)
    m1.insert(0.0, e1)
    m2 = Measure(number=2)
    c2 = Note("C4", quarterLength=2.0)
    c2.tie = Tie("stop")
    m2.insert(0.0, c2)
    part.insert(0.0, m1)
    part.insert(2.0, m2)
    score = Score()
    score.insert(0.0, part)

    raw_events, _ = _collect_events(score)
    merged_score, ok = _merge_tied_notes(score)
    merged_events, _ = _collect_events(merged_score)

    assert ok is True
    assert len(raw_events) == 3  # C4, E4 (m1) + C4 (m2)
    assert len(merged_events) == 2  # only the tied C4 chain merged; E4 untouched
    ends = sorted(round(float(e["end"]), 6) for e in merged_events)
    assert ends == [2.0, 4.0]  # untied E4 ends at 2.0; merged C4 ends at 4.0


def test_tie_free_score_outputs_preserved() -> None:
    score = Score()
    part = Part()
    part.insert(0.0, Note("C4", quarterLength=1.0))
    part.insert(1.0, Note("E4", quarterLength=1.0))
    score.insert(0.0, part)
    with tempfile.NamedTemporaryFile(suffix=".musicxml", delete=False) as tf:
        path = tf.name
    score.write("musicxml", fp=path)
    try:
        merged = analyze_vertical_cardinality(path, merge_ties=True)
        unmerged = analyze_vertical_cardinality(path, merge_ties=False)
        assert merged["series"] == unmerged["series"]
        assert merged["event_count"] == unmerged["event_count"]
    finally:
        Path(path).unlink(missing_ok=True)


def test_integration_tied_sustain_has_no_reattack_spike() -> None:
    score = _sequential_measures_score([("C4", 2.0, "start"), ("C4", 2.0, "stop")])
    with tempfile.NamedTemporaryFile(suffix=".musicxml", delete=False) as tf:
        path = tf.name
    score.write("musicxml", fp=path)
    try:
        result = analyze_vertical_cardinality(path, merge_ties=True)
        counts = [r["vertical_note_count"] for r in result["series"]]
        # One sustained event -> never more than one active note, no re-attack of 2.
        assert max(counts) == 1
        assert result["params"]["temporal_semantics"]["tie_handling"] == "merge_tied_notes"
        assert result["params"]["temporal_semantics"]["tie_merge_applied"] is True
        assert result["params"]["temporal_semantics"]["activity_interval"] == "half_open_onset_offset"
    finally:
        Path(path).unlink(missing_ok=True)


# --------------------------------------------------------------------------------------
# B. Half-open release-boundary semantics
# --------------------------------------------------------------------------------------
def test_shared_boundary_not_double_counted() -> None:
    # C4 [0, 2), D4 [2, 4): at t == 2 only D4 is active under half-open semantics.
    part = Part()
    part.insert(0.0, Note("C4", quarterLength=2.0))
    part.insert(2.0, Note("D4", quarterLength=2.0))
    score = Score()
    score.insert(0.0, part)

    by_t = _series_by_time(score, time_step=1.0)
    assert by_t[2.0]["vertical_note_count"] == 1
    assert by_t[2.0]["vertical_unique_pitch_count"] == 1
    assert by_t[2.0]["vertical_pitch_class_cardinality"] == 1
    # No artificial +1 spike anywhere in this monophonic sequence.
    assert max(r["vertical_note_count"] for r in by_t.values()) == 1


def test_final_duration_sample_drops_ended_event() -> None:
    part = Part()
    part.insert(0.0, Note("C4", quarterLength=2.0))
    score = Score()
    score.insert(0.0, part)

    by_t = _series_by_time(score, time_step=1.0)
    # At t == end (2.0) the note has already been released (half-open).
    assert by_t[2.0]["vertical_note_count"] == 0
    assert by_t[2.0]["vertical_unique_pitch_count"] == 0
    # During its sounding span it is active.
    assert by_t[0.0]["vertical_note_count"] == 1
    assert by_t[1.0]["vertical_note_count"] == 1


def test_sweep_matches_half_open_naive_with_shared_boundary() -> None:
    part = Part()
    part.insert(0.0, Note("C4", quarterLength=2.0))  # [0, 2)
    part.insert(1.0, Note("E4", quarterLength=2.0))  # [1, 3)
    part.insert(2.0, Note("G4", quarterLength=1.0))  # [2, 3)  shares boundary at t=2
    score = Score()
    score.insert(0.0, part)

    events, end_time = _collect_events(score)
    times = _time_axis(end_time, 0.5, events)
    sweep = _build_cardinality_series(times, events, reference_universe_size=REFERENCE_UNIVERSE_12TET)

    for t, row in zip(times, sweep):
        active = [ev for ev in events if ev["offset"] <= t < ev["end"]]
        notes = [n for ev in active for n in ev["notes"]]
        assert row["vertical_note_count"] == len(notes)
        assert row["vertical_unique_pitch_count"] == len({n for n in notes})

    # At the shared boundary t=2.0: C4 released, E4 + G4 active -> 2 (not 3).
    by_t = {round(float(r["time_quarters"]), 6): r for r in sweep}
    assert by_t[2.0]["vertical_note_count"] == 2


# --------------------------------------------------------------------------------------
# C. Zero-duration policy (explicit: no cardinality contribution)
# --------------------------------------------------------------------------------------
def _event(notes: list[tuple[str, float, int]], offset: float, end: float) -> dict:
    """Construct an event dict exactly as ``_collect_events`` would (12-EDO grid)."""
    return {
        "offset": offset,
        "end": end,
        "notes": notes,
        "units": [_pitch_unit(n, bin_cents=100.0) for n in notes],
        "pcs": [_pc_class(n, edo=12) for n in notes],
        "ref_units": _ref_pitch_units(notes, bin_cents=100.0),
        "raw_pitches": [],
    }


def test_zero_duration_event_contributes_no_cardinality() -> None:
    # A guaranteed zero-duration event (end == offset) alongside a sustained note.
    c4 = ("C", 0.0, 4)
    e4 = ("E", 0.0, 4)
    events = [_event([c4], 0.0, 2.0), _event([e4], 1.0, 1.0)]
    end_time = 2.0
    times = _time_axis(end_time, 1.0, events)
    series = _build_cardinality_series(times, events, reference_universe_size=REFERENCE_UNIVERSE_12TET)
    by_t = {round(float(r["time_quarters"]), 6): r for r in series}

    # The zero-duration E4 never contributes; only the sustained C4 is counted.
    assert by_t[1.0]["vertical_note_count"] == 1
    assert by_t[1.0]["vertical_unique_pitch_count"] == 1
    assert by_t[1.0]["vertical_pitch_class_cardinality"] == 1
    assert max(r["vertical_unique_pitch_count"] for r in series) == 1
    assert max(r["vertical_note_count"] for r in series) == 1
