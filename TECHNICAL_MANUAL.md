# Technical Manual — Textural-Cardinality

This manual documents the mathematics, algorithms, interpretation boundaries, and export semantics currently implemented in the codebase.

## 0. Theoretical motivation and analytical status

### 0.1 Status of the term

`Textural cardinality` is an author-defined term. It is not used here as a pre-existing standard category in music theory. It is introduced as an operational, score-based construct: the cardinality of selected sets or multisets of symbolic musical objects active at a given score-global time point.

### 0.2 Relation to texture theory

The construct isolates one quantitative aspect of vertical texture: multiplicity. It must not be equated with musical texture as a whole. Musical texture may involve number of components, registral distribution, spacing, interdependence, timbre, articulation, dynamics, orchestration, stream behaviour, and perceptual fusion. This toolkit currently measures only selected cardinalities derived from symbolic note events.

Berry’s work on texture provides the closest theoretical motivation because it treats texture partly through sounding components, their number, and their interrelations. This toolkit adopts only the restricted cardinality aspect of that broader analytical field.

Lerdahl and Jackendoff, and Lerdahl’s later pitch-space work, are relevant as precedents for explicit formalization of musical structures and pitch relations. This toolkit does not implement GTTM, prolongational analysis, tonal tension, or Tonal Pitch Space.

Tenney’s historical work on consonance and dissonance is relevant as a terminological caution. Cardinality is not consonance, dissonance, roughness, sonority, or perceptual fusion.

Roeder’s work on pitch-class/set terminology, beat-class modelling, and pulse-stream analysis is relevant as a precedent for class-based and time-sensitive analytical abstraction. This toolkit does not compute set classes, interval-class vectors, transformational relations, beat-class sets, pulse streams, or grouping structures.

### 0.3 What the metrics do not measure

The toolkit does not measure timbre, orchestration, dynamics, roughness, spectral density, loudness, or formal function. It does not perform audio-frequency analysis.

The equal-tempered pitch-class layer is symbolic. It is not a native just-intonation model, spectral tuning model, adaptive tuning model, or continuous frequency-space model.

### 0.4 Interpretation of results

A peak in `vertical_note_count` means that more symbolic note events are active at that sampled time point. It does not necessarily mean that the passage is perceptually denser, louder, orchestrationally heavier, acoustically rougher, or formally more important.

A peak in `vertical_unique_pitch_count` means that more distinct symbolic pitch units are active. It does not describe registral compression, spacing, intervallic structure, spectral content, or voice-leading behaviour.

A peak in `vertical_pitch_class_cardinality` means that more equal-tempered pitch classes are represented in the active pitch-class universe. It does not identify the set class, interval-class vector, harmonic function, tonal distance, or microtonal/intonational system beyond the selected EDO grid.

## 1) Data model and notation

The core note primitive is:

- `NoteTuple = (step, alter, octave)`
- Example: `("C", 1.0, 4)` = C-sharp 4.

For a score-global time instant `t`, let `A(t)` be the multiset of active note events.

### 1.1 Core metrics

- `vertical_note_count(t) = |A(t)|`
- `vertical_unique_pitch_count(t) = |U(t)|`, where `U(t)` is the set of active symbolic pitch units after pitch-space quantisation.
- `vertical_pitch_class_cardinality(t) = |PC_edo(t)|`, where `PC_edo(t)` is the set of active equal-tempered pitch classes under the selected EDO mapping.

### 1.2 Cardinality hierarchy and ratios

Under an aligned pitch-unit grid:

`0 <= vertical_pitch_class_cardinality(t) <= vertical_unique_pitch_count(t) <= vertical_note_count(t)`

This hierarchy is not guaranteed if `bin_cents` and `edo` are deliberately mismatched.

Useful ratios (nonzero denominators only):

- `unique_pitch_ratio(t) = vertical_unique_pitch_count(t) / vertical_note_count(t)`
- `pc_coverage_ratio(t) = vertical_pitch_class_cardinality(t) / edo`
- `pc_to_pitch_ratio(t) = vertical_pitch_class_cardinality(t) / vertical_unique_pitch_count(t)`

## 2) Pitch conversion formulas

Implemented in `iav/vertical_cardinality.py` and mirrored in `src/textural_dimension/analysis.py`.

### 2.1 Pitch-space value

For each `NoteTuple n = (step, alter, octave)`:

- `ps(n) = 12 * (octave + 1) + step_to_semitone(step) + alter`

where `step_to_semitone = {C:0, D:2, E:4, F:5, G:7, A:9, B:11}`.

### 2.2 Pitch unit quantization

- `cents(n) = 100 * ps(n)`
- `unit(n) = round(cents(n) / bin_cents)`

For `bin_cents = 100`, this is semitone-quantized pitch-space binning.

### 2.3 Pitch-class cardinality and EDO grids

Pitch-class cardinality is defined over `Z_edo = {0, 1, ..., edo - 1}`.

- `pc_edo(n) = round(ps(n) * edo / 12) mod edo`

Off-grid symbolic pitches are quantised to the nearest active grid and may appear in export `warnings`.

## 3) Event extraction from scores

Implemented in `src/textural_dimension/analysis.py::_collect_events`.

1. Traverse `score.recurse().notes`.
2. Convert local element time to score-global time with `getOffsetInHierarchy(score)`.
3. Read duration in quarter lengths.
4. Build active half-open intervals `[offset, end)`.
5. Expand chords to multiple note tuples.
6. Precompute per-event `units` and `pcs` under the active grid.

## 4) Time axis construction

Implemented in `src/textural_dimension/analysis.py::_time_axis`.

### 4.1 Instantaneous definition

Vertical cardinality is a **point measure** at score time *t*. The active multiset `A(t)` is a **piecewise-constant step function** that changes only at event onsets and offsets.

### 4.2 Event-boundary sampling (default)

The time axis is the sorted union of:

1. `0.0` and score duration `T`
2. every event **onset** `offset`
3. every event **offset** (release boundary) `end`
4. optionally, a supplementary uniform grid `{0, Δ, 2Δ, …}` while `t <= T + 1e-9`, where `Δ = max(1e-6, time_step)`

Each time point is rounded to 6 decimals for stable serialization.

### 4.3 Sampling modes

| `time_step` argument | `sampling` field | Behaviour |
|---------------------|------------------|-----------|
| positive float (default `0.25`) | `event_boundaries_with_uniform_grid` | exact boundaries + plotting grid |
| `None` | `event_boundaries_only` | minimal exact curve |

**Important:** `time_step` controls plot density, not detection completeness. Brief events shorter than `time_step` are captured because their onsets and offsets are always included.

### 4.4 What this does not do

This is not duration-weighted or window-aggregated density. A 0.01-beat event and a whole-bar chord both appear as instantaneous vertical states at their respective sample points.

## 5) Sweep-line cardinality algorithm

Implemented in `src/textural_dimension/analysis.py::_build_cardinality_series`.

At each sampled time:

1. Remove events with `end + eps <= t`
2. Add events with `offset <= t + eps`
3. Emit note count, unique pitch-unit count, pitch-class cardinality, and micro/macro fields (see §4.3.6)

Complexity: `O(E log E + W + K)` where `E` is events, `W` is sample times, and `K` is note payload processed during add/remove.

With event-boundary sampling, `W = O(E)` in the minimal mode.

### 4.3.6 Micro/macro textural cardinality (thesis alignment)

Implemented in `src/textural_dimension/analysis.py` (`reference_pitch_universe_size`, `micro_macro_normalized`, `_ref_pitch_units`).

**Reference register:** closed pitch-space interval **A0–C8** (`ps` 21.0–108.0). Only active notes whose pitch-space lies in this interval contribute to the micro/macro count.

**Reference universe size:**

| `bin_cents` | Positions in A0–C8 |
|-------------|-------------------|
| 100 (12-TET semitones) | 88 |
| 50 (quarter-tones) | 175 |
| other | derived from register span ÷ bin size |

**Metrics per series row:**

- `micro_macro_pitch_cardinality` — count of distinct quantised pitch units among active notes in A0–C8.
- `micro_macro_normalized` — `micro_macro_pitch_cardinality / reference_pitch_universe_size` (macro-referenced ratio).
- `micro_meso_macro_normalized` — three-pole texture index on `[0, 1]`:

  `(cardinality − 1) / (reference_pitch_universe_size − 1)`

**Poles (cardinality and normalized):**

| Pole | Cardinality (12-TET example) | `micro_meso_macro_normalized` |
|------|------------------------------|----------------------------------|
| **Micro** | 1 | 0.0 |
| **Meso** | `(1 + universe_size) / 2` (44.5 for 88) | 0.5 |
| **Macro** | full universe (88 or 175) | 1.0 |

Metadata is exposed under `params.micro_macro_texture` (`reference_register`, `reference_pitch_universe_size`, `micro_pole_cardinality`, `meso_pole_cardinality`, `macro_pole_cardinality`, `meso_pole_normalized`).

Auxiliary fields `vertical_note_count` and `vertical_unique_pitch_count` remain available but are not the thesis micro/macro construct.

## 6) Summary-row fallback calculations

Implemented in `iav/vertical_cardinality.py::vertical_cardinality_from_summary_row`.

- `Notes` → `vertical_note_count`
- `Unique pitches` → `vertical_unique_pitch_count` (fallback to notes if missing)
- `PC cardinality` → used only when explicitly present

No inference of pitch-class cardinality from unique-pitch counts is performed.

## 7) Output schema

Analysis output includes:

- `source_file_name`
- `time_step` — supplementary grid step, or `null`
- `sampling` — `event_boundaries_with_uniform_grid` or `event_boundaries_only`
- `duration_quarters`
- `event_count`
- `sample_count`
- `edo`
- `pitch_class_universe`
- `bin_cents`
- `params.tuning`
- `params.micro_macro_texture`
- `warnings`
- `series[]` rows containing:
  - `time_quarters`
  - `vertical_note_count`
  - `vertical_unique_pitch_count`
  - `vertical_pitch_class_cardinality`
  - `micro_macro_pitch_cardinality`
  - `micro_macro_normalized`
  - `micro_meso_macro_normalized`

CSV keeps metric column names unchanged. A leading metadata comment line records sampling, tuning, and micro/macro register metadata:

- `# sampling: …; tuning: …; micro_macro: register=A0-C8, universe_size=88; …`

## 8) Brief tutorial

### 8.1 GUI tutorial

1. Run `python -m textural_dimension` (or `run.bat`).
2. Upload a `MusicXML`, `MXL`, or `MIDI` file.
3. Configure supplementary time step and optional tuning controls (`preset`, `bin_cents`, `edo`, auto-detect).
4. Run analysis and export `CSV` / `JSON`.

### 8.2 CLI direct-input tutorial

```bash
python -m textural_dimension --notes 4 --unique-pitches 3 --pc-cardinality 2 --edo 24
```

### 8.3 Programmatic score analysis

```python
from textural_dimension.analysis import analyze_vertical_cardinality

analysis = analyze_vertical_cardinality("path/to/score.mxl")
exact = analyze_vertical_cardinality("path/to/score.mxl", time_step=None)
```

## 9) Limitations for thesis reporting

When citing results from this toolkit, state explicitly:

1. **Metric scope:** cardinality-only symbolic descriptor; not a complete texture theory.
2. **Temporal model:** instantaneous point measure at event boundaries (and optional supplementary grid points); not duration-weighted density.
3. **Pitch model:** equal-tempered pitch units and EDO pitch classes; off-grid pitches are quantised and logged in metadata.
4. **Perceptual boundary:** peaks in cardinality do not imply perceptual density, loudness, or orchestrational weight.

## 10) References

See `REFERENCES.md`.
