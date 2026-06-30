from __future__ import annotations

from pathlib import Path
import sys

from textural_cardinality.__main__ import main as cli_main
from textural_cardinality.cardinality import vertical_cardinality_for_notes


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_readme_has_no_stale_terms() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert ("Orcho" + "mogeneity") not in readme
    assert ("Aknow" + "ledgments") not in readme
    assert ("Aknow" + "ledgements") not in readme
    assert "textural_dimension" not in readme
    assert "textural-dimension" not in readme
    assert "## Acknowledgements" in readme


def test_repository_has_no_legacy_installers_token() -> None:
    stale = "insta" + "lers"
    assert not (REPO_ROOT / stale).exists()
    for path in REPO_ROOT.rglob("*"):
        if ".git" in path.parts:
            continue
        assert stale not in path.as_posix()

    for path in REPO_ROOT.rglob("*"):
        if path.is_dir() or ".git" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        assert stale not in text


def test_references_file_exists() -> None:
    assert (REPO_ROOT / "REFERENCES.md").exists()


def test_cli_direct_input_outputs_metadata(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "textural_cardinality",
            "--notes",
            "4",
            "--unique-pitches",
            "3",
            "--pc-cardinality",
            "2",
            "--edo",
            "24",
        ],
    )
    cli_main()
    out = capsys.readouterr().out
    assert '"vertical_note_count": 4' in out
    assert '"vertical_unique_pitch_count": 3' in out
    assert '"vertical_pitch_class_cardinality": 2' in out
    assert '"_metadata"' in out
    assert '"edo": 24' in out


def test_arbitrary_positive_edo_supported() -> None:
    notes = [("C", 0.0, 4), ("C", 1.0, 4)]
    card = vertical_cardinality_for_notes(notes, bin_cents=1200.0 / 31.0, edo=31)
    assert card["vertical_note_count"] == 2
    assert card["vertical_pitch_class_cardinality"] == 2
