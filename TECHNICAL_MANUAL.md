# Technical Manual — Textural cardinality

This manual documents the mathematics, algorithms, and calculations currently implemented in the codebase.

## 1) Data model and notation

The core note primitive is:

- `NoteTuple = (step, alter, octave)`
- Example: `("C", 1.0, 4)` = C-sharp 4.

For a time instant `t`, let:

- `S(t)` be the multiset of active notated pitches.
- `|S(t)|` be the total number of active note events.

The three exported metrics are:

- `vertical_note_count(t) = |S(t)|`
- `vertical_unique_pitch_count(t) = |U(t)|`, where `U(t)` is the set of quantized pitch units.
- `vertical_pitch_class_cardinality(t) = |PC_edo(t)|`, where `PC_edo(t)` is the set of pitch classes in the selected equal-tempered universe (`edo ∈ {12, 24, 48}`).

## 2) Pitch conversion formulas

Implemented in `iav/vertical_cardinality.py` and mirrored in the analysis engine.

### 2.1 Pitch-space value

For each `NoteTuple n = (step, alter, octave)`, the code computes pitch-space directly:

- `ps(n) = 12*(octave + 1) + step_to_semitone(step) + alter`

where `step_to_semitone = {C:0, D:2, E:4, F:5, G:7, A:9, B:11}`.

### 2.2 Pitch unit quantization

`bin_cents` is configurable (default `100` cents). The pitch unit is:

- `cents(n) = 100 * ps(n)`
- `unit(n) = round(cents(n) / bin_cents)`

For `bin_cents = 100`, this is equivalent to semitone-quantized MIDI bins.

### 2.3 Pitch class (EDO-parameterized)

- `pc_edo(n) = round(ps(n) * edo / 12) mod edo`
- where `edo` is configurable (default `12`; arbitrary positive EDOs accepted)

Implementation details:

- For `edo = 12`, this reduces to:
  - `pc_12(n) = round(ps(n)) mod 12`
- For `edo = 24`, one pitch-class step = 50 cents.
- For `edo = 48`, one pitch-class step = 25 cents.

## 3) Event extraction from scores

Implemented in `src/textural_dimension/analysis.py::_collect_events`.

Given a score parsed by `music21.converter.parse`:

1. Traverse `score.recurse().notes`.
2. Convert local element time to score-global time:
   - `offset = el.getOffsetInHierarchy(score)`
3. Read duration in quarter lengths:
   - `dur = el.duration.quarterLength`
4. Define active interval:
   - `[offset, end)` where `end = offset + max(0, dur)`
5. Expand chords to multiple note tuples.
6. Validate `edo ∈ {12, 24, 48}` and precompute per-event lists:
   - `units = [unit(n)]`
   - `pcs = [pc_edo(n)]`

Important correctness point: global offset conversion prevents measure/voice-local misalignment.

## 4) Time grid construction

Implemented in `src/textural_dimension/analysis.py::_time_axis`.

Given score duration `T` and step `Δ`:

- `Δ = max(1e-6, time_step)`
- `times = {0, Δ, 2Δ, ...} while t <= T + 1e-9`

Each time is rounded to 6 decimals for stable serialization.

## 5) Sweep-line cardinality algorithm

Implemented in `src/textural_dimension/analysis.py::_build_cardinality_series`.

### 5.1 Goal

Compute all metric values on the time grid without scanning every event for every time point.

### 5.2 Structures

- `starts`: events sorted by `(offset, end)`
- `ends`: events sorted by `(end, offset)`
- indices `si`, `ei` for start/end streams
- active counters:
  - `active_note_count` (int)
  - `active_units: Counter[int]`
  - `active_pcs: Counter[int]`

### 5.3 Interval convention

The active interval is half-open: `[offset, end)`.

At each time `t`:

1. Remove events with `end + eps <= t`
2. Add events with `offset <= t + eps`
3. Emit:
   - `vertical_note_count = active_note_count`
   - `vertical_unique_pitch_count = len(active_units)`
   - `vertical_pitch_class_cardinality = len(active_pcs)`

where `eps = 1e-9` is the floating-point tolerance used in code.

### 5.4 Complexity

Let:

- `E` = number of events
- `W` = number of time windows
- `K` = total note payload processed during add/remove operations

Then:

- Sorting cost: `O(E log E)`
- Sweep pass: `O(W + K)`
- Memory: `O(E + A)` where `A` is active counter footprint.

Compared with naive `O(W * E)` active-event scans, this is substantially faster on dense scores.

## 6) Summary-row fallback calculations

Implemented in `iav/vertical_cardinality.py::vertical_cardinality_from_summary_row`.

Given row fields:

- `Notes` -> `vertical_note_count` if parseable integer, else `None`
- `Unique pitches` -> integer if parseable, else:
  - fallback to `vertical_note_count` when missing/empty
- `PC cardinality` -> integer only when explicit and parseable

No inference of `PC cardinality` from `Unique pitches` is performed.

## 7) Output schema

The analysis return object contains:

- `source_file`
- `time_step`
- `duration_quarters`
- `event_count`
- `edo`
- `pitch_class_universe` (e.g., `Z12`, `Z24`, `Z48`)
- `bin_cents`
- `series[]` with rows:
  - `time_quarters`
  - `vertical_note_count`
  - `vertical_unique_pitch_count`
  - `vertical_pitch_class_cardinality`

The UI can export this as JSON and CSV.
CSV field names are unchanged; `vertical_pitch_class_cardinality` is interpreted using metadata (`edo`, `pitch_class_universe`).

## 8) Brief tutorial

### 8.1 GUI tutorial (recommended)

1. Run:
   - `python -m textural_dimension`
   - or double-click `run.bat`
2. Upload a `MusicXML`, `MXL`, or `MIDI` file.
3. Set `Time step (quarterLength)` (start with `0.25`).
4. Choose display mode:
   - `Raw Counts` for absolute values
   - `Normalized (0-1)` for comparative shape
5. Select the pitch-class universe (`12`, `24`, or `48` EDO).
6. (Optional) keep secondary axis enabled for pitch-class visibility.
7. Click **Run analysis**.
8. Download `CSV`/`JSON` for thesis plots or downstream statistics.

### 8.2 CLI quick tutorial

Use the direct row/tuple cardinality mode:

```bash
python -m textural_dimension --notes 4 --unique-pitches 3 --pc-cardinality 2 --edo 24
```

Output:

```json
{"vertical_note_count": 4, "vertical_unique_pitch_count": 3, "vertical_pitch_class_cardinality": 2}
```

