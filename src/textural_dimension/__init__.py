"""Textural dimension toolkit focused on vertical cardinality only.

See ``TECHNICAL_MANUAL.md`` for formulas, event-boundary sampling, and
interpretation boundaries.
"""

from textural_dimension.cardinality import (
    vertical_cardinality_for_notes,
    vertical_cardinality_from_summary_row,
)

__all__ = [
    "vertical_cardinality_for_notes",
    "vertical_cardinality_from_summary_row",
]
