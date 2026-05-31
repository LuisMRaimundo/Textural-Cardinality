# Textural-Cardinality

Cardinality-only symbolic toolkit with a graphical interface for score upload, analysis, and professional plotting.

## Theoretical scope

Textural cardinality is an author-defined operational construct. It denotes a family of score-derived, time-indexed cardinality descriptors for vertical symbolic texture. In this release, it measures active note-event count, distinct symbolic pitch-unit count, equal-tempered pitch-class cardinality, and a **micro/macro textural index** aligned with thesis §4.3.6: distinct pitch positions within the reference register **A0–C8**, normalized against the closed reference universe (88 semitone positions at 100-cent bins, 175 quarter-tone positions at 50-cent bins).

The construct is motivated by quantitative approaches to musical texture, especially approaches in which texture is partly described through the number of sounding components and their interrelations. It is narrower than a theory of texture. It does not model timbre, orchestration, register, spacing, density-compression, dynamics, articulation, stream segregation, perceptual salience, roughness, fusion, or formal function.

Textural cardinality should therefore be read as a reproducible symbolic descriptor, not as a complete analytical interpretation.

## Features

- Upload and analyze `MusicXML`, `MXL`, and `MIDI` files.
- Compute vertical cardinality over time with **exact event-boundary sampling** (brief sonorities are not missed):
  - `vertical_note_count`
  - `vertical_unique_pitch_count`
  - `vertical_pitch_class_cardinality`, parameterised by the selected EDO grid.
  - `micro_macro_pitch_cardinality` — distinct pitch units in **A0–C8** only (notes outside the register are excluded).
  - `micro_macro_normalized` — cardinality divided by the reference universe size (macro-referenced ratio).
  - `micro_meso_macro_normalized` — three-pole scale **micro → meso → macro** mapped to **0.0 → 0.5 → 1.0** via `(cardinality − 1) / (universe_size − 1)`.
- View results in an interactive Gradio interface with Plotly charts.
- Switch between `Raw Counts` and `Normalized (0-1)` views.
- Toggle a secondary axis for pitch-class cardinality visibility.
- Configure equal-tempered tuning via presets, `bin_cents`, `edo`, and auto-detection.
- Download analysis as `CSV` and `JSON` with sampling and tuning metadata.

## Scope and limitations

This toolkit is cardinality-only. It measures symbolic vertical multiplicity and symbolic pitch/pitch-class diversity. It does not perform audio analysis and does not estimate acoustic density, spectral density, loudness, orchestral balance, psychoacoustic roughness, or perceived textural weight.

**Temporal sampling.** Cardinality is defined instantaneously at score time *t* as the cardinality of the active symbolic note multiset *A(t)*. Because *A(t)* changes only at event onsets and offsets, the analysis **always samples at all such boundary times**, ensuring that even extremely brief vertical states are represented exactly. The configurable `time_step` adds a **supplementary uniform grid** for plotting convenience only; it does not control detection completeness.

`vertical_pitch_class_cardinality` is parameterised by the active equal-tempered pitch-class universe. The default is 12-EDO. 24-EDO and 48-EDO are useful for quarter-tone and eighth-tone symbolic encodings when the score preserves those distinctions and when an equal-tempered reduction is analytically appropriate.

Non-EDO tunings, just-intonation ratios, spectral tuning fields, and continuous frequency-space models are not represented natively. Off-grid symbolic pitches are quantised to the nearest active grid in the current implementation and reported through `warnings` in JSON metadata.

## Installation

```bash
pip install -e ".[dev]"
```

## Launch GUI

```bash
python -m textural_dimension
```

or double-click `run.bat`.

## CLI direct-input mode

This mode does not parse a score file. It computes or echoes cardinality fields from explicitly supplied summary-row values.

```bash
python -m textural_dimension --notes 4 --unique-pitches 3 --pc-cardinality 2 --edo 24
```

Example output:

```json
{
  "vertical_note_count": 4,
  "vertical_unique_pitch_count": 3,
  "vertical_pitch_class_cardinality": 2,
  "_metadata": {
    "tuning": {
      "bin_cents": 100.0,
      "edo": 24,
      "tuning_preset": null,
      "tuning_provenance": "explicit_bin_cents_edo"
    }
  }
}
```

## Programmatic API

```python
from textural_dimension.analysis import analyze_vertical_cardinality

# Default: event boundaries + supplementary grid (time_step=0.25)
result = analyze_vertical_cardinality("score.mxl")

# Minimal exact curve: event boundaries only
result = analyze_vertical_cardinality("score.mxl", time_step=None)
```

Key fields in the analysis result:

| Field | Description |
|-------|-------------|
| `sampling` | `event_boundaries_with_uniform_grid` or `event_boundaries_only` |
| `time_step` | Supplementary grid step, or `null` when omitted |
| `sample_count` | Number of time points in `series` |
| `event_count` | Number of extracted note/chord events |
| `params.tuning` | Active `bin_cents`, `edo`, preset, and provenance |
| `params.micro_macro_texture` | Reference register A0–C8, universe size (88/175), micro/meso/macro pole cardinalities |
| `series` | Time-indexed cardinality rows |

## Analysis behavior

- Uses score-global offsets (`getOffsetInHierarchy`) for temporal correctness.
- Uses an incremental sweep-line engine for efficient dense-score processing.
- **Always includes every event onset and offset** in the analysis time axis.
- Defaults to `time_step=0.25` quarter-length as a supplementary plotting grid (configurable in the UI; set to `None` in code for event-only sampling).
- Uses symbolic equal-tempered quantisation grids (`bin_cents`, `edo`) and does not model acoustic tuning systems.
- JSON includes active grid metadata (`edo`, `pitch_class_universe`, `bin_cents`, `params.tuning`, `sampling`, `sample_count`) plus `warnings` when non-grid pitches are quantised.
- CSV keeps metric column names unchanged and prepends a metadata comment line for sampling and tuning.

## Documentation

- Technical manual (formulas, algorithms, and interpretation): [`TECHNICAL_MANUAL.md`](TECHNICAL_MANUAL.md)
- Bibliographic references: [`REFERENCES.md`](REFERENCES.md)

## License

Copyright © 2026 Luís Raimundo and contributors. All rights reserved.

## Terms of use

This software and its documentation are proprietary. No open-source licence is granted by this repository or by [`NOTICE.md`](NOTICE.md). You may not copy, modify, merge, publish, distribute, sublicense, or sell copies of this software, or use it for commercial purposes, except as expressly permitted in writing by the copyright holder.

Academic and research use may be permitted under separate agreement or institutional policy; when in doubt, contact the author before redistribution or derivative distribution.

Third-party components: runtime dependencies (e.g. Python packages listed in `pyproject.toml`) are subject to their respective licences. This notice governs the Textural-Cardinality application source, documentation, and branding only.

## Contact

For licensing enquiries, cite the repository maintainer listed in [`CITATION.cff`](CITATION.cff).

email: lmr.2020@outlook.pt

## Acknowledgements

This project was developed by Luís Raimundo with the support and funding of the Fundação para a Ciência e a Tecnologia (FCT) and Universidade NOVA de Lisboa.

Funding DOI: https://doi.org/10.54499/2020.08817.BD

The author also gratefully acknowledges Isabel Pires for her support throughout the development of this work.
