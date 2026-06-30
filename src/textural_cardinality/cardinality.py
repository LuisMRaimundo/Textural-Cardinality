"""Public wrappers for vertical cardinality operations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import importlib.util
from pathlib import Path
from typing import Any

_IAV_PATH = Path(__file__).resolve().parents[2] / "iav" / "vertical_cardinality.py"
_IAV_SPEC = importlib.util.spec_from_file_location("textural_cardinality._iav_vertical_cardinality", _IAV_PATH)
if _IAV_SPEC is None or _IAV_SPEC.loader is None:
    raise ImportError(f"Could not load local IAV module at {_IAV_PATH}")
_IAV_MODULE = importlib.util.module_from_spec(_IAV_SPEC)
_IAV_SPEC.loader.exec_module(_IAV_MODULE)
_vertical_cardinality_for_notes = _IAV_MODULE.vertical_cardinality_for_notes
_vertical_cardinality_from_summary_row = _IAV_MODULE.vertical_cardinality_from_summary_row

NoteTuple = tuple[str, float, int]


def vertical_cardinality_for_notes(
    notes: Sequence[NoteTuple],
    *,
    bin_cents: float = 100.0,
    edo: int = 12,
) -> dict[str, int | None]:
    """Compute vertical cardinality for an explicit note tuple sequence."""
    return _vertical_cardinality_for_notes(notes, bin_cents=bin_cents, edo=edo)


def vertical_cardinality_from_summary_row(
    row: Mapping[str, Any],
    *,
    bin_cents: float = 100.0,
    edo: int = 12,
) -> dict[str, int | None]:
    """Recover vertical cardinality fields from one summary-row dictionary."""
    return _vertical_cardinality_from_summary_row(row, bin_cents=bin_cents, edo=edo)
