"""Public wrappers for vertical cardinality operations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from iav.vertical_cardinality import (
    vertical_cardinality_for_notes as _vertical_cardinality_for_notes,
)
from iav.vertical_cardinality import (
    vertical_cardinality_from_summary_row as _vertical_cardinality_from_summary_row,
)

NoteTuple = tuple[str, float, int]


def vertical_cardinality_for_notes(
    notes: Sequence[NoteTuple],
    *,
    bin_cents: int = 100,
    edo: int = 12,
) -> dict[str, int | None]:
    """Compute vertical cardinality for an explicit note tuple sequence."""
    return _vertical_cardinality_for_notes(notes, bin_cents=bin_cents, edo=edo)


def vertical_cardinality_from_summary_row(
    row: Mapping[str, Any],
    *,
    bin_cents: int = 100,
    edo: int = 12,
) -> dict[str, int | None]:
    """Recover vertical cardinality fields from one summary-row dictionary."""
    return _vertical_cardinality_from_summary_row(row, bin_cents=bin_cents, edo=edo)
