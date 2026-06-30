"""Micro-corpus regression fixtures for vertical-cardinality output stability."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest

from textural_cardinality.__main__ import run_analyze_score
from textural_cardinality.analysis import analyze_vertical_cardinality

CORPUS_DIR = Path(__file__).resolve().parent / "fixtures" / "regression_corpus"
EXPECTED_DIR = CORPUS_DIR / "expected"

ORDERING_FIXTURES = (
    "monophony",
    "dyad",
    "triad",
    "chromatic_cluster",
)

CARDINALITY_FIELDS = (
    "vertical_note_count",
    "vertical_unique_pitch_count",
    "vertical_pitch_class_cardinality",
)

CORPUS_FIXTURES = tuple(
    path.stem for path in sorted(CORPUS_DIR.glob("*.musicxml"))
)


def _expected_path(name: str) -> Path:
    return EXPECTED_DIR / f"{name}.json"


def _score_path(name: str) -> Path:
    return CORPUS_DIR / f"{name}.musicxml"


def _load_expected(name: str) -> dict[str, Any]:
    return json.loads(_expected_path(name).read_text(encoding="utf-8"))


def _analysis_kwargs(expected: dict[str, Any]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"time_step": None}
    options = expected.get("analysis_options", {})
    if preset := options.get("tuning_preset"):
        kwargs["tuning_preset"] = preset
    return kwargs


def _compact_series(series: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "time_quarters": row["time_quarters"],
            **{field: row[field] for field in CARDINALITY_FIELDS},
        }
        for row in series
    ]


def _stable_snapshot(analysis: dict[str, Any]) -> dict[str, Any]:
    series = analysis["series"]
    return {
        "event_count": analysis["event_count"],
        "sample_count": analysis["sample_count"],
        "max_vertical_note_count": max(row["vertical_note_count"] for row in series),
        "max_vertical_unique_pitch_count": max(row["vertical_unique_pitch_count"] for row in series),
        "max_vertical_pitch_class_cardinality": max(
            row["vertical_pitch_class_cardinality"] for row in series
        ),
        "edo": analysis["edo"],
        "bin_cents": analysis["bin_cents"],
        "sampling": analysis["sampling"],
        "duration_quarters": analysis["duration_quarters"],
        "series": _compact_series(series),
        "params": {
            "temporal_semantics": analysis["params"]["temporal_semantics"],
            "tuning": {
                "bin_cents": analysis["params"]["tuning"]["bin_cents"],
                "edo": analysis["params"]["tuning"]["edo"],
                "tuning_preset": analysis["params"]["tuning"]["tuning_preset"],
                "tuning_provenance": analysis["params"]["tuning"]["tuning_provenance"],
            },
        },
    }


def _analyze_fixture(name: str) -> dict[str, Any]:
    expected = _load_expected(name)
    return analyze_vertical_cardinality(str(_score_path(name)), **_analysis_kwargs(expected))


def _cli_argv(name: str, *, csv_path: Path, json_path: Path) -> list[str]:
    argv = [
        str(_score_path(name)),
        "--output-csv",
        str(csv_path),
        "--output-json",
        str(json_path),
        "--event-boundaries-only",
    ]
    preset = _load_expected(name).get("analysis_options", {}).get("tuning_preset")
    if preset:
        argv.extend(["--tuning-preset", preset])
    return argv


@pytest.mark.parametrize("fixture_name", CORPUS_FIXTURES)
def test_fixture_loads_and_returns_valid_result(fixture_name: str) -> None:
    analysis = _analyze_fixture(fixture_name)
    assert analysis["event_count"] > 0
    assert analysis["sample_count"] >= 2
    assert analysis["series"]
    assert analysis["params"]["temporal_semantics"]["activity_interval"] == "half_open_onset_offset"


def _regression_expected(expected: dict[str, Any]) -> dict[str, Any]:
    """Expected snapshot fields only (exclude test-run metadata)."""
    return {key: value for key, value in expected.items() if key != "analysis_options"}


@pytest.mark.parametrize("fixture_name", CORPUS_FIXTURES)
def test_expected_scalar_regression(fixture_name: str) -> None:
    expected = _regression_expected(_load_expected(fixture_name))
    snapshot = _stable_snapshot(_analyze_fixture(fixture_name))
    assert snapshot == expected


@pytest.mark.parametrize("fixture_name", CORPUS_FIXTURES)
def test_cli_export_regression(fixture_name: str, tmp_path: Path) -> None:
    csv_path = tmp_path / f"{fixture_name}.csv"
    json_path = tmp_path / f"{fixture_name}.json"
    exit_code = run_analyze_score(_cli_argv(fixture_name, csv_path=csv_path, json_path=json_path))
    assert exit_code == 0
    assert csv_path.is_file()
    assert json_path.is_file()

    expected = _regression_expected(_load_expected(fixture_name))
    exported = json.loads(json_path.read_text(encoding="utf-8"))
    snapshot = _stable_snapshot(exported)

    assert snapshot == expected
    assert "temporal_semantics" in exported["params"]
    assert exported["params"]["temporal_semantics"]["activity_interval"] == "half_open_onset_offset"

    csv_rows = list(csv.DictReader(csv_path.read_text(encoding="utf-8").splitlines()[1:]))
    assert len(csv_rows) == expected["sample_count"]
    assert int(csv_rows[0]["vertical_note_count"]) == expected["series"][0]["vertical_note_count"]


def test_max_vertical_note_count_ordering_regression() -> None:
    peaks = {
        name: _load_expected(name)["max_vertical_note_count"] for name in ORDERING_FIXTURES
    }
    ordered = [peaks[name] for name in ORDERING_FIXTURES]
    assert ordered == sorted(ordered)
    assert ordered[0] < ordered[-1]
    assert peaks["monophony"] == 1
    assert peaks["dyad"] == 2
    assert peaks["triad"] == 3
    assert peaks["chromatic_cluster"] == 5


def test_tied_sustain_does_not_inflate_attacks() -> None:
    expected = _load_expected("tied_sustain")
    analysis = _analyze_fixture("tied_sustain")

    assert expected["event_count"] == 1
    assert expected["max_vertical_note_count"] == 1
    assert all(row["vertical_note_count"] <= 1 for row in analysis["series"])
    assert analysis["params"]["temporal_semantics"]["tie_merge_applied"] is True


def test_shared_boundary_has_no_release_spike() -> None:
    expected = _load_expected("shared_boundary")
    by_time = {row["time_quarters"]: row for row in expected["series"]}

    assert expected["max_vertical_note_count"] == 1
    assert by_time[2.0]["vertical_note_count"] == 1
    assert by_time[2.0]["vertical_unique_pitch_count"] == 1
    assert by_time[4.0]["vertical_note_count"] == 0


@pytest.mark.parametrize("fixture_name", CORPUS_FIXTURES)
def test_analysis_is_stable_across_repeated_runs(fixture_name: str) -> None:
    first = _stable_snapshot(_analyze_fixture(fixture_name))
    second = _stable_snapshot(_analyze_fixture(fixture_name))
    assert first == second
