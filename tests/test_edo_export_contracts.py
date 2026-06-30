"""Robustness contracts for arbitrary EDO grids and CSV/JSON export."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import tempfile

import pytest
from music21.chord import Chord
from music21.note import Note
from music21.pitch import Pitch
from music21.stream import Part, Score

from textural_cardinality.analysis import (
    TUNING_PRESETS,
    analyze_vertical_cardinality,
    detect_tuning_grid,
    write_cardinality_csv,
    write_cardinality_json,
    _collect_events,
)

CSV_METRIC_FIELDS = [
    "time_quarters",
    "vertical_note_count",
    "vertical_unique_pitch_count",
    "vertical_pitch_class_cardinality",
    "micro_macro_pitch_cardinality",
    "micro_macro_normalized",
    "micro_meso_macro_normalized",
]

INTERPRETIVE_RATIO_FIELDS = [
    "unique_pitch_ratio",
    "pc_coverage_ratio",
    "pc_to_pitch_ratio",
]


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


def _hierarchy_holds(row: dict[str, int]) -> bool:
    pc = int(row["vertical_pitch_class_cardinality"])
    unique = int(row["vertical_unique_pitch_count"])
    notes = int(row["vertical_note_count"])
    return 0 <= pc <= unique <= notes


@pytest.mark.parametrize("preset_name", ["19_edo", "31_edo", "53_edo"])
def test_explicit_edo_presets_do_not_crash(preset_name: str) -> None:
    preset = TUNING_PRESETS[preset_name]
    edo = int(preset["edo"])
    step = 12.0 / float(edo)
    ps_values = [60.0, 60.0 + step, 60.0 + 2.0 * step]
    path = _write_score_with_ps(ps_values)
    try:
        result = analyze_vertical_cardinality(
            path,
            tuning_preset=preset_name,
            time_step=None,
        )
        assert result["edo"] == edo
        assert math.isclose(float(result["bin_cents"]), float(preset["bin_cents"]))
        assert result["series"]
        for row in result["series"]:
            assert row["vertical_note_count"] >= 0
            assert row["vertical_unique_pitch_count"] >= 0
            assert row["vertical_pitch_class_cardinality"] >= 0
    finally:
        Path(path).unlink(missing_ok=True)


@pytest.mark.parametrize("preset_name", ["19_edo", "31_edo", "53_edo"])
def test_explicit_edo_bin_cents_combinations_produce_finite_rows(preset_name: str) -> None:
    preset = TUNING_PRESETS[preset_name]
    path = _write_score_with_ps([60.0, 64.0, 67.0])
    try:
        result = analyze_vertical_cardinality(
            path,
            bin_cents=float(preset["bin_cents"]),
            edo=int(preset["edo"]),
            auto_detect_tuning=False,
            time_step=None,
        )
        assert result["sample_count"] == len(result["series"]) > 0
        assert all(math.isfinite(float(row["time_quarters"])) for row in result["series"])
        assert result["params"]["tuning"]["tuning_provenance"] == "explicit_bin_cents_edo"
    finally:
        Path(path).unlink(missing_ok=True)


@pytest.mark.parametrize("preset_name", ["19_edo", "31_edo", "53_edo"])
def test_pitch_class_cardinality_bounded_by_edo(preset_name: str) -> None:
    preset = TUNING_PRESETS[preset_name]
    edo = int(preset["edo"])
    step = 12.0 / float(edo)
    ps_values = [60.0 + k * step for k in range(min(edo, 6))]
    path = _write_score_with_ps(ps_values)
    try:
        result = analyze_vertical_cardinality(
            path,
            tuning_preset=preset_name,
            time_step=None,
        )
        for row in result["series"]:
            assert 0 <= row["vertical_pitch_class_cardinality"] <= edo
    finally:
        Path(path).unlink(missing_ok=True)


@pytest.mark.parametrize("preset_name", ["19_edo", "31_edo", "53_edo"])
def test_coherent_grid_hierarchy_holds(preset_name: str) -> None:
    preset = TUNING_PRESETS[preset_name]
    step = 12.0 / float(preset["edo"])
    ps_values = [60.0, 60.0 + step, 60.0 + 2.0 * step]
    path = _write_score_with_ps(ps_values)
    try:
        result = analyze_vertical_cardinality(
            path,
            tuning_preset=preset_name,
            time_step=None,
        )
        assert all(_hierarchy_holds(row) for row in result["series"])
    finally:
        Path(path).unlink(missing_ok=True)


def test_microtonal_cents_offsets_binned_consistently_under_31_edo() -> None:
    preset = TUNING_PRESETS["31_edo"]
    step = 12.0 / 31.0
    ps_a = 60.0
    ps_b = 60.0 + step
    path = _write_score_with_ps([ps_a, ps_b])
    try:
        result = analyze_vertical_cardinality(
            path,
            tuning_preset="31_edo",
            time_step=None,
        )
        row = result["series"][0]
        assert row["vertical_unique_pitch_count"] == 2
        assert row["vertical_pitch_class_cardinality"] == 2

        score = Score(id="test")
        part = Part(id="p1")
        part.insert(0.0, Chord([Pitch(ps=ps_a), Pitch(ps=ps_b)], quarterLength=1.0))
        score.insert(0.0, part)
        events, _ = _collect_events(
            score,
            edo=31,
            bin_cents=float(preset["bin_cents"]),
        )
        units = events[0]["units"]
        pcs = events[0]["pcs"]
        assert len(set(units)) == 2
        assert len(set(pcs)) == 2
        assert all(0 <= pc < 31 for pc in pcs)
    finally:
        Path(path).unlink(missing_ok=True)


def test_incoherent_bin_cents_edo_may_break_hierarchy() -> None:
    """Document current behaviour: mismatched grid parameters are not normalised."""
    path = _write_score_with_ps([60.0, 60.5, 61.0])
    try:
        result = analyze_vertical_cardinality(
            path,
            bin_cents=100.0,
            edo=31,
            auto_detect_tuning=False,
            time_step=None,
        )
        row = result["series"][0]
        assert row["vertical_note_count"] == 3
        # Semitone binning collapses 60.0 and 60.5 to one unit while 31-EDO PCs can differ.
        assert row["vertical_unique_pitch_count"] <= row["vertical_note_count"]
        assert row["vertical_pitch_class_cardinality"] <= 31
        assert not _hierarchy_holds(row)
    finally:
        Path(path).unlink(missing_ok=True)


def test_arbitrary_edo_auto_detect_selects_largest_compatible_grid_in_scan_range() -> None:
    """Beyond 12/24/48 fast paths, auto-detect scans edo in [2, 240] and keeps the last fit."""
    events = [
        {
            "raw_pitches": [
                {"part_index": 0, "beat": 0.0, "ps": 60.0},
                {"part_index": 0, "beat": 0.0, "ps": 60.0 + 12.0 / 19.0},
            ]
        }
    ]
    detected = detect_tuning_grid(events)
    assert detected["detected_edo"] == 228
    assert math.isclose(float(detected["detected_bin_cents"]), 1200.0 / 228.0)


def test_auto_detect_with_music21_ps_may_select_higher_edo_due_to_float_tolerance() -> None:
    """music21 pitch-space floats can fail strict 19-EDO checks; document the fallback path."""
    step = 12.0 / 19.0
    path = _write_score_with_ps([60.0, 60.0 + step, 60.0 + 2.0 * step])
    try:
        auto = analyze_vertical_cardinality(path, auto_detect_tuning=True, time_step=None)
        explicit = analyze_vertical_cardinality(
            path,
            tuning_preset="19_edo",
            time_step=None,
        )
        assert auto["params"]["tuning"]["tuning_provenance"] == "auto_detected"
        assert auto["edo"] >= 19
        assert explicit["edo"] == 19
        assert auto["series"]
    finally:
        Path(path).unlink(missing_ok=True)


def test_csv_export_contract() -> None:
    path = _write_score_with_ps([60.0, 64.0, 67.0])
    try:
        analysis = analyze_vertical_cardinality(path, time_step=None)
        csv_path = write_cardinality_csv(analysis)
        try:
            text = Path(csv_path).read_text(encoding="utf-8")
            lines = text.splitlines()
            assert lines[0].startswith("# sampling: ")
            assert "tuning:" in lines[0]
            assert "micro_macro:" in lines[0]
            assert "event_count=" in lines[0]

            reader = csv.DictReader(lines[1:])
            assert reader.fieldnames == CSV_METRIC_FIELDS
            rows = list(reader)
            assert len(rows) == len(analysis["series"])
            for exported, source in zip(rows, analysis["series"]):
                for field in CSV_METRIC_FIELDS:
                    assert exported[field] == str(source[field])
            for ratio in INTERPRETIVE_RATIO_FIELDS:
                assert ratio not in (reader.fieldnames or [])
        finally:
            Path(csv_path).unlink(missing_ok=True)
    finally:
        Path(path).unlink(missing_ok=True)


def test_json_export_contract() -> None:
    path = _write_score_with_ps([60.0, 60.5])
    try:
        analysis = analyze_vertical_cardinality(path, bin_cents=50.0, edo=24, time_step=None)
        json_path = write_cardinality_json(analysis)
        try:
            exported = json.loads(Path(json_path).read_text(encoding="utf-8"))
            for key in (
                "source_file_name",
                "sampling",
                "duration_quarters",
                "event_count",
                "sample_count",
                "edo",
                "pitch_class_universe",
                "bin_cents",
                "warnings",
                "params",
                "series",
            ):
                assert key in exported

            assert "temporal_semantics" in exported["params"]
            assert exported["params"]["temporal_semantics"]["activity_interval"] == "half_open_onset_offset"
            assert "tuning" in exported["params"]
            assert "micro_macro_texture" in exported["params"]
            assert exported["series"] == analysis["series"]
            assert exported["edo"] == analysis["edo"]
            assert exported["bin_cents"] == analysis["bin_cents"]

            for row in exported["series"]:
                for field in CSV_METRIC_FIELDS:
                    assert field in row
                for ratio in INTERPRETIVE_RATIO_FIELDS:
                    assert ratio not in row
        finally:
            Path(json_path).unlink(missing_ok=True)
    finally:
        Path(path).unlink(missing_ok=True)


def test_export_preserves_direct_analysis_values() -> None:
    path = _write_score_with_ps([60.0, 64.0])
    try:
        analysis = analyze_vertical_cardinality(path, time_step=0.5)
        csv_path = write_cardinality_csv(analysis)
        json_path = write_cardinality_json(analysis)
        try:
            csv_lines = Path(csv_path).read_text(encoding="utf-8").splitlines()
            csv_rows = list(csv.DictReader(csv_lines[1:]))
            json_rows = json.loads(Path(json_path).read_text(encoding="utf-8"))["series"]
            for csv_row, json_row, source_row in zip(csv_rows, json_rows, analysis["series"]):
                assert int(csv_row["vertical_note_count"]) == source_row["vertical_note_count"]
                assert int(json_row["vertical_note_count"]) == source_row["vertical_note_count"]
                assert int(csv_row["vertical_pitch_class_cardinality"]) == source_row[
                    "vertical_pitch_class_cardinality"
                ]
                assert json_row["micro_macro_pitch_cardinality"] == source_row[
                    "micro_macro_pitch_cardinality"
                ]
        finally:
            Path(csv_path).unlink(missing_ok=True)
            Path(json_path).unlink(missing_ok=True)
    finally:
        Path(path).unlink(missing_ok=True)
