# Verification record — 2026-10-13

The development outcomes below were executed on the delivery machine. Subsequent
GitHub publication and passing Windows/Linux CI are recorded in [PUBLICATION.md](PUBLICATION.md).
WSL2 and the larger reference study remain untested.

## Environment

Windows CPU, Python 3.14.2, NumPy 2.4.0, Pandas 2.3.3, SciPy 1.17.1,
scikit-learn 1.9.1, PyTorch 2.14.1+cpu, SymPy 1.14.0, Matplotlib 3.10.8,
Gradio 6.16.0, pytest 9.1.1, PySR 2.7.0, Julia 1.11.9,
SymbolicRegression.jl 2.7.0 and Ruff 0.17.0.

The development environment was created with `python -m venv --system-site-packages
.venv`, reusing installed numerical/Torch packages. scikit-learn, PySR and Ruff
were installed into this environment. requirements.txt pins the recorded direct
versions; results/environment.freeze.txt captures the broader reused environment.
A fresh fully isolated environment was not rebuilt locally. Python package
Requires-Python metadata permits 3.11 for these dependencies, but the 3.11
runtime and remote CI matrix remain unverified.

## Executed commands and outcomes

All commands were run from the repository root using `.venv\Scripts\python.exe`.
For the Julia-enabled commands the environment was:

```powershell
$env:JULIA_DEPOT_PATH = 'E:\AI\symbolic-discovery-lab\.julia'
$env:PYTHON_JULIACALL_THREADS = '1'
```

| Command (interpreter abbreviated as python) | Actual outcome |
| --- | --- |
| `python -m pip install --no-build-isolation --no-deps -e .` | Editable package installed |
| `python -m pytest -q --basetemp=runs/pytest-stage1` | 11 passed, 1 opt-in Julia test skipped |
| `python scripts/check_pysr.py` | Official Julia initialized, real PySR search succeeded; wall 1410.58 s |
| `python -m pytest -q --basetemp=runs/pytest-stage2` | 16 passed, 1 skipped |
| `python -m symbolic_discovery run --config configs/smoke.json --output results/smoke` | 6 fits, zero failures |
| `python -m symbolic_discovery run --config configs/quick.json --models polynomial mlp --output results/baselines` | 90 fits, zero failures |
| `python -m symbolic_discovery run --config configs/quick.json --output results/quick` | 135 fits, zero failures |
| `python -m symbolic_discovery run --config configs/smoke.json --models polynomial mlp pysr --output results/smoke_all` | Final integrated path: 9 fits, zero failures |
| `python -m pytest -q --basetemp=runs/pytest-release` | 26 passed, 1 opt-in Julia test skipped, 39.75 s |
| `RUN_PYSR_TESTS=1; python -m pytest -q --basetemp=runs/pytest-release-julia` | **27 passed**, 1 intentional thread-count warning, 67.27 s |
| `python scripts/verify_demo.py --include-symbolic` | Real HTTP/API sequence polynomial → MLP → PySR → all succeeded; PNG responses and metric rows checked |
| `python scripts/verify_results.py --results results/quick` | 45 data conditions hashed; 135 successful fits; 540 metric rows recomputed; 5 PNG/SVG pairs parsed |
| `python scripts/verify_results.py --results results/smoke_all` | 3 conditions; 9 fits; 36 metric rows; 5 figure pairs checked |
| `python -m ruff check src tests scripts app.py` | No lint errors |
| `python -m ruff format --check src tests scripts app.py` | Formatting check passed |
| `python -m pip check` | No broken requirements |
| `python -m pip wheel --no-deps --no-build-isolation . --wheel-dir runs/wheels` | Wheel built; final build includes demo_worker.py |
| `python scripts/build_showcase.py` | README generated from the 135-fit study |

The shell notation RUN_PYSR_TESTS=1 in the table denotes setting
`$env:RUN_PYSR_TESTS = '1'` in PowerShell before the exact pytest command.
The tests explicitly initialize Julia before collection imports Torch.

## Repairs and scientific audit

Tests were written before implementation, initially failing on missing modules.
Review regressions were also observed failing before their corresponding fixes.
These intentional red steps are development evidence, not final passing claims.

- Initial sandbox downloads failed with WinError 10013; authorized dependency
  downloads outside the network restriction succeeded. No dependency absence
  was inferred from the network error.
- The default pytest temp root was inaccessible in the restricted environment.
  Creating runs/ and directing basetemp there resolved the permission issue.
- Independent review identified failed-fit plot leakage, premature completion,
  partial demo results, UI runtime ordering and coefficient export precision.
  Each material issue was corrected and verified; see CODE_REVIEW.md.
- Eager SymPy parsing hid removable domain holes. `evaluate=False` now preserves
  arithmetic during probes. All stored expression checks were regenerated with
  `python -m symbolic_discovery reevaluate --results results/quick` (also baselines
  and smoke); initial evaluation CSVs remain preserved.
- Round-trip polynomial export was repaired with
  `python scripts/reexport_polynomials.py --results results/quick`, and the same
  command for baselines, smoke and smoke_all. **96** deterministic polynomial
  reconstructions passed stored-prediction consistency checks. Original metric
  CSVs, training durations and PySR/MLP fits were retained. No polynomial symbolic
  recovery success was removed because the recorded initial rates had none.
- The first full study emitted JuliaCall's warning about importing Torch first.
  It completed with no process failure. The final CLI initializes Julia first;
  the UI uses isolated request workers, and the real model-switch sequence passed.
- The one-thread warning in Julia checks is expected: PySR normally recommends
  auto threads, but this project's default serial reproducible search uses one.

## Figure and artifact checks

Five figure types were opened for visual inspection: truth/prediction, noise,
data efficiency, ID/OOD and PySR validation Pareto front. Labels, legends and
uncertainty definitions are readable; PNG and editable SVG pairs were verified.
Log plots use a 1e-12 display floor only, so numerically exact fits can overlap.
Raw unfloored values remain in CSV tables. Sample SD is descriptive and is not
a confidence interval. No p-values or significance conclusions are claimed.

The result integrity checker recomputes RMSE/MAE/R² from saved predictions,
checks split SHA256 hashes and OOD support, matches selected PySR candidates to
validation minima, rechecks aggregated statistics, and parses figures/reports.

## Not run / limitations

- `configs/reference.json` (five seeds and longer searches): not run.
- WSL2, Linux/macOS runtime and Python 3.11: not run locally.
- GitHub Actions matrix: defined but not executed on a remote repository.
- Fully isolated fresh dependency installation: instructions provided, not rebuilt.
- Independent scientific replication, significance tests and real measurement
  datasets: not performed.
- The initial development delivery was local. On 2026-10-14 the user requested
  publication; the complete project was published to the specified GitHub repository,
  and all four CPU CI jobs passed. See PUBLICATION.md for the exact commit/run.
