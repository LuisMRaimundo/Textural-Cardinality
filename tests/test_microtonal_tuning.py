from __future__ import annotations

import math
from pathlib import Path
import tempfile

from music21.chord import Chord
from music21.note import Note
from music21.pitch import Pitch
from music21.stream import Part, Score

from textural_dimension.analysis import (
    _collect_events,
    _non_grid_pitches,
    analyze_vertical_cardinality,
    detect_tuning_grid,
    write_cardinality_csv,
)


def _write_score_with_ps(ps_values: list[float]) -> str:
    score = Score()
    part = Part()
    chord_pitches = [Pitch(ps=ps) for ps in ps_values]
    ch = Chord(chord_pitches, quarterLength=1.0)
    part.insert(0.0, ch)
    score.insert(0.0, part)
    with tempfile.NamedTemporaryFile(suffix=".musicxml", delete=False) as tf:
        path = tf.name
    score.write("musicxml", fp=path)
    return path


def test_semitone_default_unchanged() -> None:
    path = _write_score_with_ps([60.0, 64.0])
    try:
        default_result = analyze_vertical_cardinality(path)
        explicit_result = analyze_vertical_cardinality(
            path,
            bin_cents=100.0,
            edo=12,
            auto_detect_tuning=False,
        )
        assert default_result == explicit_result
    finally:
        Path(path).unlink(missing_ok=True)


def test_explicit_quartertone_grid() -> None:
    path = _write_score_with_ps([60.0, 60.5])
    try:
        quarter = analyze_vertical_cardinality(path, bin_cents=50.0, edo=24)
        default = analyze_vertical_cardinality(path)
        assert quarter["series"][0]["vertical_unique_pitch_count"] == 2
        assert quarter["series"][0]["vertical_pitch_class_cardinality"] == 2
        assert default["series"][0]["vertical_unique_pitch_count"] == 1
        assert default["series"][0]["vertical_pitch_class_cardinality"] == 1
    finally:
        Path(path).unlink(missing_ok=True)


def test_auto_detect_quartertone() -> None:
    path = _write_score_with_ps([60.0, 60.5])
    try:
        auto = analyze_vertical_cardinality(path, auto_detect_tuning=True)
        explicit = analyze_vertical_cardinality(path, bin_cents=50.0, edo=24)
        assert auto["series"] == explicit["series"]
        tuning = auto["params"]["tuning"]
        assert tuning["tuning_provenance"] == "auto_detected"
        assert tuning["edo"] == 24
        assert math.isclose(float(tuning["bin_cents"]), 50.0)
    finally:
        Path(path).unlink(missing_ok=True)


def test_auto_detect_eighthtone() -> None:
    score = Score()
    part = Part()
    for ps in [60.0, 60.25]:
        n = Note(quarterLength=1.0)
        n.pitch = Pitch(ps=ps)
        part.insert(0.0, n)
    score.insert(0.0, part)

    events, _ = _collect_events(score)
    detected = detect_tuning_grid(events)
    assert detected["detected_edo"] == 48
    assert math.isclose(float(detected["detected_bin_cents"]), 25.0)


def test_non_grid_pitch_warning() -> None:
    path = _write_score_with_ps([60.0, 60.5])
    try:
        result = analyze_vertical_cardinality(path)
        warnings = result.get("warnings", [])
        assert any(w.get("code") == "non_grid_pitches" for w in warnings)

        score = Score()
        part = Part()
        n1 = Note(quarterLength=1.0)
        n1.pitch = Pitch(ps=60.0)
        n2 = Note(quarterLength=1.0)
        n2.pitch = Pitch(ps=60.25)
        part.insert(0.0, n1)
        part.insert(0.0, n2)
        score.insert(0.0, part)
        events, _ = _collect_events(score)
        assert _non_grid_pitches(events, bin_cents=50.0)
    finally:
        Path(path).unlink(missing_ok=True)


def test_tuning_recorded_in_export() -> None:
    path = _write_score_with_ps([60.0, 60.5])
    try:
        result = analyze_vertical_cardinality(path, bin_cents=50.0, edo=24)
        tuning = result["params"]["tuning"]
        assert "bin_cents" in tuning
        assert "edo" in tuning
        assert "tuning_provenance" in tuning
        assert "tuning_preset" in tuning

        csv_path = write_cardinality_csv(result)
        try:
            first_line = Path(csv_path).read_text(encoding="utf-8").splitlines()[0]
            assert first_line.startswith("# tuning: ")
            assert "edo=24" in first_line
        finally:
            Path(csv_path).unlink(missing_ok=True)
    finally:
        Path(path).unlink(missing_ok=True)
