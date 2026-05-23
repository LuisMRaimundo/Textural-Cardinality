"""CLI entrypoint for cardinality-only analysis."""

from __future__ import annotations

import argparse
import json
import sys

from textural_dimension.analysis import DEFAULT_BIN_CENTS, DEFAULT_EDO, TUNING_PRESETS
from textural_dimension.cardinality import vertical_cardinality_from_summary_row


def main() -> None:
    if len(sys.argv) == 1:
        from textural_dimension.ui.gradio_app import main as run_gradio_app

        run_gradio_app()
        return

    parser = argparse.ArgumentParser(
        description=(
            "Vertical cardinality direct-input mode. "
            "This CLI path does not parse a score file; it uses supplied summary-row values."
        )
    )
    parser.add_argument("--notes", type=int, default=0, help="Direct input value for 'Notes'.")
    parser.add_argument("--unique-pitches", type=int, default=0, help="Direct input value for 'Unique pitches'.")
    parser.add_argument("--pc-cardinality", type=int, default=None, help="Optional explicit direct input for 'PC cardinality'.")
    parser.add_argument("--bin-cents", type=float, default=DEFAULT_BIN_CENTS, help="Pitch quantization grid in cents.")
    parser.add_argument(
        "--edo",
        type=int,
        default=DEFAULT_EDO,
        help="Pitch-class universe (EDO) for cardinality calculations.",
    )
    parser.add_argument(
        "--auto-detect-tuning",
        action="store_true",
        help="Enable score-driven tuning auto-detection when not explicitly set.",
    )
    parser.add_argument(
        "--tuning-preset",
        choices=sorted(TUNING_PRESETS.keys()),
        default=None,
        help="Convenience preset for (bin_cents, edo).",
    )
    args = parser.parse_args()

    active_bin_cents = float(args.bin_cents)
    active_edo = int(args.edo)
    active_preset: str | None = None
    provenance = "default_12_edo"
    explicit_params = (abs(active_bin_cents - DEFAULT_BIN_CENTS) > 1e-9) or (active_edo != DEFAULT_EDO)
    if explicit_params:
        provenance = "explicit_bin_cents_edo"
    elif args.tuning_preset is not None:
        preset = TUNING_PRESETS[args.tuning_preset]
        active_bin_cents = float(preset["bin_cents"])
        active_edo = int(preset["edo"])
        active_preset = args.tuning_preset
        provenance = "tuning_preset"
    elif args.auto_detect_tuning:
        provenance = "auto_detected"
    else:
        active_preset = "12_edo"

    row = {"Notes": args.notes, "Unique pitches": args.unique_pitches}
    if args.pc_cardinality is not None:
        row["PC cardinality"] = args.pc_cardinality
    output = vertical_cardinality_from_summary_row(row, bin_cents=active_bin_cents, edo=active_edo)
    output["_metadata"] = {
        "tuning": {
            "bin_cents": active_bin_cents,
            "edo": active_edo,
            "tuning_preset": active_preset,
            "tuning_provenance": provenance,
        }
    }
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
