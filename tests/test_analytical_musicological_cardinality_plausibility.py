"""Analytical-musicological plausibility contracts for symbolic vertical cardinality.

These tests validate that controlled symbolic textures yield ordinally plausible
cardinality relationships. They do not judge aesthetic quality and do not use audio.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile
from typing import Callable

from music21.chord import Chord
from music21.note import Note
from music21.pitch import Pitch
from music21.stream import Part, Score
from music21.tie import Tie

from textural_cardinality.analysis import (
    analyze_vertical_cardinality,
    write_cardinality_csv,
    write_cardinality_json,
)


def _write_score(score: Score) -> str:
    with tempfile.NamedTemporaryFile(suffix=".musicxml", delete=False) as tf:
        path = tf.name
    score.write("musicxml", fp=path)
    return path


def _analyze(build: Callable[[Score], None], **kwargs: object) -> dict:
    score = Score()
    build(score)
    path = _write_score(score)
    try:
        return analyze_vertical_cardinality(path, time_step=None, **kwargs)
    finally:
        Path(path).unlink(missing_ok=True)


def _peak(analysis: dict, field: str) -> int:
    return max(int(row[field]) for row in analysis["series"])


def _row_at(analysis: dict, time_quarters: float = 0.0) -> dict:
    for row in analysis["series"]:
        if float(row["time_quarters"]) == float(time_quarters):
            return row
    raise AssertionError(f"No series row at t={time_quarters}")


def _simultaneous_chord_part(pitch_names: list[str], duration: float = 1.0) -> Callable[[Score], None]:
    def build(score: Score) -> None:
        part = Part()
        for name in pitch_names:
            part.insert(0.0, Note(name, quarterLength=duration))
        score.insert(0.0, part)

    return build


# --------------------------------------------------------------------------------------
# A. Monophony vs polyphony
# --------------------------------------------------------------------------------------
def test_monophony_dyad_triad_cluster_vertical_cardinality_increases() -> None:
    mono = _analyze(_simultaneous_chord_part(["C4"]))
    dyad = _analyze(_simultaneous_chord_part(["C4", "E4"]))
    triad = _analyze(_simultaneous_chord_part(["C4", "E4", "G4"]))
    cluster = _analyze(_simultaneous_chord_part(["C4", "C#4", "D4", "D#4", "E4", "F4"]))

    mono_peak = _peak(mono, "vertical_note_count")
    dyad_peak = _peak(dyad, "vertical_note_count")
    triad_peak = _peak(triad, "vertical_note_count")
    cluster_peak = _peak(cluster, "vertical_note_count")

    assert mono_peak == 1
    assert mono_peak < dyad_peak < triad_peak < cluster_peak


# --------------------------------------------------------------------------------------
# B. Unison doubling vs distinct pitch content
# --------------------------------------------------------------------------------------
def test_unison_doubling_inflates_note_count_not_pitch_diversity() -> None:
    def build(score: Score) -> None:
        part_a = Part()
        part_b = Part()
        part_a.insert(0.0, Note("C4", quarterLength=1.0))
        part_b.insert(0.0, Note("C4", quarterLength=1.0))
        score.insert(0.0, part_a)
        score.insert(0.0, part_b)

    analysis = _analyze(build)
    row = _row_at(analysis, 0.0)
    assert row["vertical_note_count"] == 2
    assert row["vertical_unique_pitch_count"] == 1
    assert row["vertical_pitch_class_cardinality"] == 1


# --------------------------------------------------------------------------------------
# C. Octave doubling vs pitch-class cardinality
# --------------------------------------------------------------------------------------
def test_octave_doubling_preserves_single_twelve_tet_pitch_class() -> None:
    analysis = _analyze(_simultaneous_chord_part(["C4", "C5"]))
    row = _row_at(analysis, 0.0)
    assert row["vertical_note_count"] == 2
    assert row["vertical_unique_pitch_count"] == 2
    assert row["vertical_pitch_class_cardinality"] == 1


# --------------------------------------------------------------------------------------
# D. Enharmonic equivalence
# --------------------------------------------------------------------------------------
def test_enharmonic_spellings_share_one_pitch_class_in_twelve_tet() -> None:
    analysis = _analyze(_simultaneous_chord_part(["C#4", "Db4"]))
    row = _row_at(analysis, 0.0)
    assert row["vertical_note_count"] == 2
    assert row["vertical_unique_pitch_count"] == 1
    assert row["vertical_pitch_class_cardinality"] == 1


# --------------------------------------------------------------------------------------
# E. Pitch-class saturation
# --------------------------------------------------------------------------------------
def test_chromatic_aggregate_reaches_twelve_pitch_classes_and_octave_doubling_does_not_raise_pc() -> None:
    chromatic = ["C4", "C#4", "D4", "D#4", "E4", "F4", "F#4", "G4", "G#4", "A4", "A#4", "B4"]

    def build_twelve_pc(score: Score) -> None:
        part = Part()
        for name in chromatic:
            part.insert(0.0, Note(name, quarterLength=1.0))
        score.insert(0.0, part)

    def build_with_octave_double(score: Score) -> None:
        part = Part()
        for name in chromatic:
            part.insert(0.0, Note(name, quarterLength=1.0))
        part.insert(0.0, Note("C5", quarterLength=1.0))
        score.insert(0.0, part)

    twelve = _analyze(build_twelve_pc)
    doubled = _analyze(build_with_octave_double)
    row12 = _row_at(twelve, 0.0)
    row13 = _row_at(doubled, 0.0)

    assert row12["vertical_pitch_class_cardinality"] == 12
    assert row13["vertical_pitch_class_cardinality"] == 12
    assert row13["vertical_note_count"] > row12["vertical_note_count"]
    assert row13["vertical_unique_pitch_count"] > row12["vertical_unique_pitch_count"]


# --------------------------------------------------------------------------------------
# F. Microtonal cardinality
# --------------------------------------------------------------------------------------
def test_quarter_tone_distinctions_raise_unique_pitch_cardinality_under_24_edo() -> None:
    def build(score: Score) -> None:
        part = Part()
        part.insert(0.0, Note(quarterLength=1.0))
        part[0].pitch = Pitch(ps=60.0)
        part.insert(0.0, Note(quarterLength=1.0))
        part[1].pitch = Pitch(ps=60.5)
        score.insert(0.0, part)

    default = _analyze(build)
    quarter_tone = _analyze(build, bin_cents=50.0, edo=24)

    default_row = _row_at(default, 0.0)
    micro_row = _row_at(quarter_tone, 0.0)

    assert default_row["vertical_unique_pitch_count"] == 1
    assert micro_row["vertical_unique_pitch_count"] == 2
    assert micro_row["vertical_pitch_class_cardinality"] == 2
    assert micro_row["vertical_pitch_class_cardinality"] <= 24
    assert micro_row["vertical_note_count"] == 2


# --------------------------------------------------------------------------------------
# G. Temporal overlap / texture
# --------------------------------------------------------------------------------------
def test_sequential_non_overlapping_events_keep_lower_peak_than_overlapping_texture() -> None:
    def sequential(score: Score) -> None:
        part = Part()
        part.insert(0.0, Note("C4", quarterLength=2.0))
        part.insert(2.0, Note("E4", quarterLength=2.0))
        score.insert(0.0, part)

    def overlapping(score: Score) -> None:
        part = Part()
        part.insert(0.0, Note("C4", quarterLength=4.0))
        part.insert(2.0, Note("E4", quarterLength=2.0))
        score.insert(0.0, part)

    seq_peak = _peak(_analyze(sequential), "vertical_note_count")
    ovl_peak = _peak(_analyze(overlapping), "vertical_note_count")
    assert seq_peak == 1
    assert ovl_peak == 2
    assert seq_peak < ovl_peak


def test_counterpoint_overlap_reaches_two_voice_cardinality() -> None:
    def build(score: Score) -> None:
        voice_a = Part()
        voice_b = Part()
        voice_a.insert(0.0, Note("C4", quarterLength=4.0))
        voice_a.insert(4.0, Note("D4", quarterLength=4.0))
        voice_b.insert(2.0, Note("E4", quarterLength=4.0))
        voice_b.insert(6.0, Note("F4", quarterLength=4.0))
        score.insert(0.0, voice_a)
        score.insert(0.0, voice_b)

    analysis = _analyze(build)
    assert _peak(analysis, "vertical_note_count") == 2
    overlap_rows = [row for row in analysis["series"] if int(row["vertical_note_count"]) == 2]
    assert overlap_rows


def test_homorhythmic_chord_exceeds_monophonic_line_peak() -> None:
    melody = _analyze(_simultaneous_chord_part(["C4"], duration=2.0))
    chord = _analyze(_simultaneous_chord_part(["C4", "E4", "G4"], duration=2.0))
    assert _peak(melody, "vertical_note_count") == 1
    assert _peak(chord, "vertical_note_count") == 3
    assert _peak(melody, "vertical_note_count") < _peak(chord, "vertical_note_count")


# --------------------------------------------------------------------------------------
# H. Ties and sustained texture (integrated musical scenarios)
# --------------------------------------------------------------------------------------
def test_tied_sustain_with_overlapping_independent_voice_behaves_plausibly() -> None:
    def build(score: Score) -> None:
        part = Part()
        sustain_start = Note("C4", quarterLength=4.0)
        sustain_start.tie = Tie("start")
        sustain_stop = Note("C4", quarterLength=4.0)
        sustain_stop.tie = Tie("stop")
        part.insert(0.0, sustain_start)
        part.insert(4.0, sustain_stop)
        part.insert(2.0, Note("E4", quarterLength=2.0))
        score.insert(0.0, part)

    analysis = _analyze(build)
    by_time = {float(row["time_quarters"]): row for row in analysis["series"]}

    assert by_time[0.0]["vertical_note_count"] == 1
    assert by_time[2.0]["vertical_note_count"] == 2
    assert by_time[4.0]["vertical_note_count"] == 1
    assert _peak(analysis, "vertical_note_count") == 2
    assert by_time[0.0]["vertical_note_count"] < by_time[2.0]["vertical_note_count"]


# --------------------------------------------------------------------------------------
# I. Macro / micro texture fields
# --------------------------------------------------------------------------------------
def test_wide_register_texture_exceeds_compact_micro_macro_cardinality() -> None:
    compact = _analyze(_simultaneous_chord_part(["C4"]))
    wide = _analyze(_simultaneous_chord_part(["C2", "G3", "C5", "C7"]))

    compact_mm = _row_at(compact, 0.0)["micro_macro_pitch_cardinality"]
    wide_mm = _row_at(wide, 0.0)["micro_macro_pitch_cardinality"]

    assert compact_mm == 1
    assert wide_mm > compact_mm
    assert 0.0 <= float(_row_at(wide, 0.0)["micro_meso_macro_normalized"]) <= 1.0
    assert float(_row_at(wide, 0.0)["micro_macro_normalized"]) <= 1.0


# --------------------------------------------------------------------------------------
# J. Export / result consistency
# --------------------------------------------------------------------------------------
def test_export_preserves_monophony_to_cluster_cardinality_ordering() -> None:
    textures = {
        "mono": _analyze(_simultaneous_chord_part(["C4"])),
        "dyad": _analyze(_simultaneous_chord_part(["C4", "E4"])),
        "triad": _analyze(_simultaneous_chord_part(["C4", "E4", "G4"])),
        "cluster": _analyze(_simultaneous_chord_part(["C4", "C#4", "D4", "D#4", "E4", "F4"])),
    }
    peaks = {name: _peak(analysis, "vertical_note_count") for name, analysis in textures.items()}
    assert peaks["mono"] < peaks["dyad"] < peaks["triad"] < peaks["cluster"]

    for analysis in textures.values():
        csv_path = write_cardinality_csv(analysis)
        json_path = write_cardinality_json(analysis)
        try:
            csv_rows = list(csv.DictReader(Path(csv_path).read_text(encoding="utf-8").splitlines()[1:]))
            json_rows = json.loads(Path(json_path).read_text(encoding="utf-8"))["series"]
            assert csv_rows
            assert json_rows == analysis["series"]
            for field in (
                "vertical_note_count",
                "vertical_unique_pitch_count",
                "vertical_pitch_class_cardinality",
                "micro_macro_pitch_cardinality",
            ):
                assert field in csv_rows[0]
                assert field in json_rows[0]
            exported_peak = max(int(row["vertical_note_count"]) for row in csv_rows)
            source_peak = _peak(analysis, "vertical_note_count")
            assert exported_peak == source_peak
        finally:
            Path(csv_path).unlink(missing_ok=True)
            Path(json_path).unlink(missing_ok=True)
