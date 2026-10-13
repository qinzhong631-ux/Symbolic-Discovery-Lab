# Symbolic Discovery Lab implementation plan

Goal: an independent CPU research project with measured, reproducible evidence.

Architecture: immutable split containers feed train-only model adapters. Validation
selects PySR candidates and MLP checkpoints. Evaluation alone accesses the oracle.
One runner pairs seeds and writes raw records before aggregation and plotting.

Constraints: no changes to MiniGPT; no copied PySR implementation; no oracle
templates, guesses, coefficient priors or recovery-based candidate selection.
Python/Matplotlib is the requested figure backend. A common search grammar
(`+`, `-`, `*`, `/`, `sin`) is used across datasets, with configurable budgets.

## Stage 1
- [x] Write tests for seeded independent splits, nested training sets, shell OOD,
  formula evaluation and strict-versus-approximate recovery; observe failure.
- [x] Implement `data.py`, `metrics.py`, lazy `models/symbolic.py` and packaging.
- [x] Run unit tests and try real Julia/PySR initialization and a tiny search.

## Stage 2
- [x] Test train-only polynomial scaling, CPU MLP learning/checkpoint restore,
  validation candidate selection, aggregation and end-to-end artifact generation.
- [x] Implement adapters, experiment CLI, JSON configs, provenance, plots/report.
- [x] Run paired multi-seed comparisons, preserve failures, inspect five figures.

## Stage 3
- [x] Test Demo callback with baseline and invalid controls.
- [x] Implement Gradio UI; verify local HTTP/API interaction.
- [x] Review code independently, repair material findings, rerun final checks.
- [x] Write English README, experiment interpretation, validation and handoff.

Verification commands: `python -m pytest -q`; `python -m symbolic_discovery run
--config configs/smoke.json --output results/smoke`; `python -m symbolic_discovery
run --config configs/quick.json --output results/quick`; `python scripts/verify_demo.py`.
The reference configuration has a larger search budget; quick results must be
labeled exploratory. Failed searches are recorded and excluded from metrics,
with success counts always shown. Standard deviations use ddof=1; n=1 has no SD.
