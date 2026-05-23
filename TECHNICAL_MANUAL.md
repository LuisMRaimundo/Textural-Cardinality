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

Let `A(t)` be the multiset of active note events at score-global time `t`.

`vertical_note_count(t) = |A(t)|`

Let `U(t)` be the set of active symbolic pitch units after pitch-space quantisation.

`vertical_unique_pitch_count(t) = |U(t)|`

Let `PC_edo(t)` be the set of active equal-tempered pitch classes under the selected EDO mapping.

`vertical_pitch_class_cardinality(t) = |PC_edo(t)|`

Interpretation of reductions:

- `vertical_note_count` counts events with multiplicity.
- `vertical_unique_pitch_count` collapses duplicate pitch units but preserves register.
- `vertical_pitch_class_cardinality` collapses octave/register identity into the selected pitch-class universe.

Containment statement:

Under an aligned pitch-unit grid, where `bin_cents` is compatible with the selected EDO and pitch units refine or equal the EDO pitch-class grid, the usual relationship is:

`0 <= vertical_pitch_class_cardinality(t) <= vertical_unique_pitch_count(t) <= vertical_note_count(t)`

This hierarchy is not guaranteed if `bin_cents` and `edo` are deliberately mismatched, because unique pitch units and pitch classes are then being counted on different quantisation grids.

Ratio interpretation for nonzero denominators:

- `unique_pitch_ratio(t) = vertical_unique_pitch_count(t) / vertical_note_count(t)`
- `pc_coverage_ratio(t) = vertical_pitch_class_cardinality(t) / edo`
- `pc_to_pitch_ratio(t) = vertical_pitch_class_cardinality(t) / vertical_unique_pitch_count(t)`

`unique_pitch_ratio` measures how much event multiplicity survives after duplicate pitch units are collapsed.

`pc_coverage_ratio` measures occupancy of the selected pitch-class universe.

Under aligned quantisation, `pc_to_pitch_ratio` is a register-folding ratio: values near `1` indicate that most active pitch units occupy distinct pitch classes; lower values indicate more octave/register duplication of the same pitch classes. Do not compute or interpret ratio values with zero denominator.

## 2) Pitch conversion formulas

Implemented in `iav/vertical_cardinality.py` and mirrored in `src/textural_dimension/analysis.py`.

### 2.1 Pitch-space value

For each `NoteTuple n = (step, alter, octave)`, the code computes pitch-space directly:

- `ps(n) = 12 * (octave + 1) + step_to_semitone(step) + alter`

where `step_to_semitone = {C:0, D:2, E:4, F:5, G:7, A:9, B:11}`.

### 2.2 Pitch unit quantization

`bin_cents` is configurable (default `100` cents). The pitch unit is:

- `cents(n) = 100 * ps(n)`
- `unit(n) = round(cents(n) / bin_cents)`

For `bin_cents = 100`, this is semitone-quantized pitch-space binning.

### 2.3 Pitch-class cardinality and EDO grids

The current implementation defines pitch-class cardinality over an equal-tempered pitch-class universe `Z_edo`.

- `Z_edo = {0, 1, ..., edo - 1}`

The default is 12-EDO. Common presets include 24-EDO and 48-EDO. Additional equal-tempered grids are available through `edo` and `bin_cents`.

The pitch-class mapping is:

- `pc_edo(n) = round(ps(n) * edo / 12) mod edo`

where `ps(n)` is the symbolic pitch-space value.

Consequences:

1. The metric is not a just-intonation or spectral-harmony model.
2. Off-grid or non-EDO tunings are quantised to the nearest active EDO grid when encountered.
3. The metric should not be used as evidence of acoustic roughness, spectral density, psychoacoustic dissonance, or continuous microtonal diversity.
4. Publications using this metric on microtonal repertoire should report active `edo`, `bin_cents`, tuning preset/provenance, and any warnings.

## 3) Event extraction from scores

Implemented in `src/textural_dimension/analysis.py::_collect_events`.

Given a score parsed by `music21.converter.parse`:

1. Traverse `score.recurse().notes`.
2. Convert local element time to score-global time with `getOffsetInHierarchy(score)`.
3. Read duration in quarter lengths.
4. Build active half-open intervals `[offset, end)`.
5. Expand chords to multiple note tuples.
6. Precompute per-event `units` and `pcs` under the active grid.

Global offset conversion is essential for measure/voice-local alignment correctness.

## 4) Time grid construction

Implemented in `src/textural_dimension/analysis.py::_time_axis`.

Given score duration `T` and step `Δ`:

- `Δ = max(1e-6, time_step)`
- `times = {0, Δ, 2Δ, ...}` while `t <= T + 1e-9`

Each time point is rounded to 6 decimals for stable serialization.

## 5) Sweep-line cardinality algorithm

Implemented in `src/textural_dimension/analysis.py::_build_cardinality_series`.

At each sampled time:

1. Remove events whose `end` is before or at `t`.
2. Add events whose `offset` is before or at `t`.
3. Emit note count, unique pitch-unit count, and pitch-class cardinality.

The implementation uses counters for active units and active pitch classes to avoid naive full rescans.

## 6) Summary-row fallback calculations

Implemented in `iav/vertical_cardinality.py::vertical_cardinality_from_summary_row`.

For direct-input summary rows:

- `Notes` is parsed as `vertical_note_count`.
- `Unique pitches` is parsed as `vertical_unique_pitch_count` (fallback to notes if missing).
- `PC cardinality` is used only when explicitly present.

No inference of pitch-class cardinality from unique pitches is performed.

## 7) Output schema

Analysis output includes:

- `source_file`
- `time_step`
- `duration_quarters`
- `event_count`
- `edo`
- `pitch_class_universe`
- `bin_cents`
- `params.tuning`
- `warnings`
- `series[]` rows containing:
  - `time_quarters`
  - `vertical_note_count`
  - `vertical_unique_pitch_count`
  - `vertical_pitch_class_cardinality`

CSV keeps metric column names unchanged. The current CSV writer prepends one metadata comment line:

- `# tuning: bin_cents=<...>, edo=<...>, preset=<...>, provenance=<...>`

## 8) Brief tutorial

### 8.1 GUI tutorial

1. Run `python -m textural_dimension` (or `run.bat`).
2. Upload a `MusicXML`, `MXL`, or `MIDI` file.
3. Configure time step and optional tuning controls (`preset`, `bin_cents`, `edo`, auto-detect).
4. Run analysis and export `CSV` / `JSON`.

### 8.2 CLI direct-input tutorial

This mode does not parse score files. It computes/echoes cardinality from provided summary-row values.

```bash
python -m textural_dimension --notes 4 --unique-pitches 3 --pc-cardinality 2 --edo 24
```

## 9) References

See `REFERENCES.md`.

