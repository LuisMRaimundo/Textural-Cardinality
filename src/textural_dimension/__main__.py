"""CLI entrypoint for cardinality-only analysis."""

from __future__ import annotations

import argparse
import json
import sys

from textural_dimension.cardinality import vertical_cardinality_from_summary_row


def main() -> None:
    if len(sys.argv) == 1:
        from textural_dimension.ui.gradio_app import main as run_gradio_app

        run_gradio_app()
        return

    parser = argparse.ArgumentParser(description="Vertical cardinality (cardinality-only build).")
    parser.add_argument("--notes", type=int, default=0, help="Value for 'Notes'.")
    parser.add_argument("--unique-pitches", type=int, default=0, help="Value for 'Unique pitches'.")
    parser.add_argument("--pc-cardinality", type=int, default=None, help="Optional explicit PC cardinality.")
    parser.add_argument(
        "--edo",
        type=int,
        choices=[12, 24, 48],
        default=12,
        help="Pitch-class universe for cardinality calculations: 12, 24, or 48.",
    )
    args = parser.parse_args()
    row = {"Notes": args.notes, "Unique pitches": args.unique_pitches}
    if args.pc_cardinality is not None:
        row["PC cardinality"] = args.pc_cardinality
    print(
        json.dumps(
            vertical_cardinality_from_summary_row(row, edo=args.edo),
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
