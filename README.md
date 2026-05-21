# Textural cardinality

Cardinality-only symbolic toolkit with a graphical interface for score upload, analysis, and professional plotting.

## Features

- Upload and analyze `MusicXML`, `MXL`, and `MIDI` files.
- Compute vertical cardinality over time:
  - `vertical_note_count`
  - `vertical_unique_pitch_count`
  - `vertical_pitch_class_cardinality`
- View results in an interactive Gradio interface with Plotly charts.
- Switch between `Raw Counts` and `Normalized (0-1)` views.
- Toggle a secondary axis for pitch-class cardinality visibility.
- Inspect peak-note annotations and summary statistics (min/max/mean).
- Download analysis as `CSV` and `JSON`.
- Use direct cardinality wrappers for script workflows.

## Installation

```bash
pip install -e ".[dev]"
```

## Launch GUI

```bash
python -m textural_dimension
```

or double-click `run.bat`.

## CLI quick mode

```bash
python -m textural_dimension --notes 4 --unique-pitches 3 --pc-cardinality 2
```

## Analysis behavior

- Uses score-global offsets (`getOffsetInHierarchy`) for temporal correctness.
- Uses an incremental sweep-line engine for efficient dense-score processing.
- Defaults to `time_step=0.25` quarter-length, configurable in the UI.

## Documentation

- Technical manual (formulas, algorithms, calculations, tutorial):
  - `TECHNICAL_MANUAL.md`


## License
Copyright © 2026 Luís Raimundo and contributors. All rights reserved.

## Terms of use
This software and its documentation are proprietary. No open-source licence is granted by this repository or by NOTICE.md. You may not copy, modify, merge, publish, distribute, sublicense, or sell copies of this software, or use it for commercial purposes, except as expressly permitted in writing by the copyright holder.

Academic and research use may be permitted under separate agreement or institutional policy; when in doubt, contact the author before redistribution or derivative distribution.

Third-party components
Runtime dependencies (e.g. Python packages listed in pyproject.toml) are subject to their respective licences. This notice governs the Orchomogeneity application source and branding only.

## Contact
For licensing enquiries, cite the repository maintainer listed in CITATION.cff
 
## Aknowledgments

This project was developed by Luís Raimundo with the support and funding of the Fundação para a Ciência e a Tecnologia (FCT) and Universidade NOVA de Lisboa.

Funding DOI: https://doi.org/10.54499/2020.08817.BD

The author also gratefully acknowledges Isabel Pires for her support throughout the development of this work.
