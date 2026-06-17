# Regression corpus fixtures

Synthetic symbolic MusicXML scores used only for **output-stability regression** in
`tests/test_regression_micro_corpus.py` (31 tests; see `TECHNICAL_MANUAL.md` §10.3).

- Fixtures are small, hand-curated or programmatically generated test scores — not a
  representative musical corpus and not a claim about repertoire.
- They do **not** validate perception, acoustics, or musicological interpretation.
- Expected JSON snapshots freeze stable scalar cardinality outputs and selected series
  rows under the project's v1.1.0 temporal semantics (`[onset, offset)` activity,
  tied-note merging).

If analysis formulas, temporal semantics, or export contracts change intentionally,
update the expected files in `expected/` together with the code change.
