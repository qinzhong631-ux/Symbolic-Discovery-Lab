# Installation and platform notes

## Windows CPU (primary workflow)

Use Python 3.11 or newer. The measured environment is Python 3.14.2 on Windows
with PyTorch 2.14.1+cpu. Other Python/platform combinations need verification.
Create a fresh environment for independent use:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
python -m pip install --no-deps -e .
```

If activation is blocked by your PowerShell policy, invoke the interpreter
directly, e.g. `.\.venv\Scripts\python.exe -m pytest -q`. Activation is optional.
The development verification reused existing scientific packages with
`python -m venv --system-site-packages .venv`; this is disclosed in the validation
record. The installation instructions above produce an isolated environment.

Direct Python dependencies are pinned in requirements.txt. pyproject.toml offers
compatible version ranges and an optional symbolic extra for baseline-only
installations: `python -m pip install -e ".[dev]"` or `-e ".[dev,symbolic]"`.
The full environment snapshot is an audit record, not a portable lock file.

## Initialize the official Julia backend

PySR 2.7.0 uses JuliaCall/juliapkg. `import pysr` downloads a compatible Julia
and installs SymbolicRegression.jl automatically when needed. This requires
network access and several minutes/disk space for download and precompilation.
Do not use obsolete `pysr.install()` instructions.

Keep the depot local to the project and retain it between runs:

```powershell
$env:JULIA_DEPOT_PATH = "$PWD\.julia"
$env:PYTHON_JULIACALL_THREADS = "1"
python scripts/check_pysr.py
```

The check writes a real success/failure record in `results/backend_check/`.
The official automatic installer selected Julia 1.11.9 for this development run.
The ordinary experiment runner retains one process across searches, avoiding
repeated Julia JIT within a suite. A new CLI invocation still has startup cost.
Serial search is configured with `deterministic=True` and explicit random_state.
The thread environment variable must be set **before** importing PySR.

For an already installed compatible Julia, JuliaCall supports an explicit
executable override:

```powershell
$env:PYTHON_JULIAPKG_EXE = 'C:\path\to\julia.exe'
python scripts/check_pysr.py
```

Only set this to an actual executable compatible with the installed PySR
juliapkg constraints. Do not change Julia versions midway through a benchmark.

## Failure diagnosis

- Network errors: verify access to PyPI, julialang-s3.julialang.org,
  pkg.julialang.org and GitHub. A sandbox's WinError 10013 is a network permission
  failure, not proof that the package does not exist.
- Long first import: let Julia installation/precompilation complete. Keep the
  process alive and inspect the log before interpreting compilation as a hang.
- Interrupted install: check for active Julia/Python processes before investigating
  a stale juliapkg lock. Never remove a lock belonging to a running installer.
- Prediction poles: division is in the search grammar; candidates may be finite
  on training inputs but singular elsewhere. Nonfinite test/OOD predictions mark
  that fit failed; no substitute formula is inserted.
- Testing in a restricted environment: create `runs/`, then use
  `python -m pytest -q --basetemp=runs/pytest-local`.

If PySR cannot initialize, run real baselines independently:

```powershell
python -m symbolic_discovery run --config configs/quick.json --models polynomial mlp --output runs/baselines-new
```

This explicitly changes the model list and records it. A missing PySR result is
never replaced with synthetic performance numbers.

## WSL2 alternative (not verified in this delivery)

Install an Ubuntu WSL2 distribution and Python 3.11+ using your system package
manager or a Python environment manager. Create the repository and environment
inside the Linux filesystem rather than sharing the Windows `.venv`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
python -m pip install --no-deps -e .
export JULIA_DEPOT_PATH="$PWD/.julia"
export PYTHON_JULIACALL_THREADS=1
python scripts/check_pysr.py
python -m symbolic_discovery run --config configs/quick.json --output runs/quick-wsl
```

Do not reuse Windows wheels or compiled Julia artifacts inside WSL2. See the
[PySR installation guide](https://pysr.ai/install), [official Agent guide](https://github.com/astroautomata/PySR/blob/master/skills/pysr/SKILL.md),
and [JuliaCall configuration](https://juliapy.github.io/PythonCall.jl/stable/juliacall/)
for current upstream requirements.
