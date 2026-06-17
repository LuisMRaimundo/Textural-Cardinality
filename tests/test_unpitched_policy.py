"""Contract tests for unpitched / percussion exclusion policy."""

from __future__ import annotations

from pathlib import Path
import tempfile

from music21.note import Note, Unpitched
from music21.stream import Part, Score

from textural_dimension.analysis import _collect_events, analyze_vertical_cardinality


def _write_score(score: Score) -> str:
    with tempfile.NamedTemporaryFile(suffix=".musicxml", delete=False) as tf:
        path = tf.name
    score.write("musicxml", fp=path)
    return path


def test_unpitched_only_score_does_not_crash_and_yields_zero_cardinality() -> None:
    score = Score()
    part = Part()
    part.insert(0.0, Unpitched("D", quarterLength=1.0))
    score.insert(0.0, part)

    events, end_time = _collect_events(score)
    assert events == []
    assert end_time == 0.0

    path = _write_score(score)
    try:
        result = analyze_vertical_cardinality(path, time_step=None)
        assert result["event_count"] == 0
        assert all(row["vertical_note_count"] == 0 for row in result["series"])
        assert all(row["vertical_unique_pitch_count"] == 0 for row in result["series"])
        assert all(row["vertical_pitch_class_cardinality"] == 0 for row in result["series"])
    finally:
        Path(path).unlink(missing_ok=True)


def test_mixed_pitched_and_unpitched_counts_only_pitched_notes() -> None:
    score = Score()
    part = Part()
    part.insert(0.0, Note("C4", quarterLength=1.0))
    part.insert(0.0, Unpitched("D", quarterLength=1.0))
    score.insert(0.0, part)

    events, _ = _collect_events(score)
    assert len(events) == 1
    assert len(events[0]["notes"]) == 1

    path = _write_score(score)
    try:
        result = analyze_vertical_cardinality(path, time_step=None)
        row = result["series"][0]
        assert row["vertical_note_count"] == 1
        assert row["vertical_unique_pitch_count"] == 1
        assert row["vertical_pitch_class_cardinality"] == 1
    finally:
        Path(path).unlink(missing_ok=True)
