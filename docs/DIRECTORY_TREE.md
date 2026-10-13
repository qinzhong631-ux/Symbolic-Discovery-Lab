# Delivery directory

```text
symbolic-discovery-lab/
├── README.md
├── LICENSE
├── CITATION.cff
├── HANDOFF.md
├── app.py
├── pyproject.toml
├── requirements.txt
├── .gitignore
├── .github/workflows/tests.yml
├── src/symbolic_discovery/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── data.py
│   ├── metrics.py
│   ├── experiments.py
│   ├── runtime.py
│   ├── plotting.py
│   ├── report.py
│   ├── demo.py
│   ├── demo_worker.py
│   └── models/
│       ├── __init__.py
│       ├── symbolic.py
│       ├── polynomial.py
│       └── mlp.py
├── configs/
│   ├── smoke.json
│   ├── quick.json
│   └── reference.json
├── tests/
│   ├── conftest.py
│   ├── test_data_metrics.py
│   ├── test_symbolic.py
│   ├── test_baselines_runner.py
│   ├── test_demo.py
│   └── test_runtime.py
├── scripts/
│   ├── check_pysr.py
│   ├── verify_demo.py
│   ├── verify_results.py
│   ├── reexport_polynomials.py
│   ├── build_showcase.py
│   ├── package_release.py
│   ├── prepare_publication.py
│   └── run_experiments.ps1
├── licenses/THIRD_PARTY.md
├── docs/
│   ├── INSTALLATION.md
│   ├── METHODS.md
│   ├── EXPERIMENTS.md
│   ├── FIGURE_CONTRACT.md
│   ├── IMPLEMENTATION_PLAN.md
│   ├── CODE_REVIEW.md
│   ├── DIRECTORY_TREE.md
│   ├── VALIDATION.md
│   ├── PUBLICATION.md
│   └── handoffs/2026-10-13-delivery.md
└── results/
    ├── environment.freeze.txt
    ├── JuliaProject.toml
    ├── JuliaManifest.toml
    ├── demo_check.json
    ├── artifact_inventory.csv
    ├── backend_check/
    │   └── status.json + upstream search files
    ├── quick/                 # 135 fits, 45 data conditions
    ├── baselines/             # 90 fits, 45 data conditions
    ├── smoke/                 # 6 fits, 3 data conditions
    └── smoke_all/             # 9 fits, 3 data conditions
```

Each study directory contains manifest.json, metrics.csv, summary.csv, REPORT.md,
formula_recovery.csv, formula_recovery_summary.csv, initial/before-fix recovery
archives, evaluation_revision.json, polynomial_export_revision.json and figures/.
The verified quick and final smoke directories also contain integrity_check.json.

Figures are truth_prediction, noise_robustness, data_efficiency, id_ood and
pareto_frontier, each in PNG and SVG. Every data condition has:

```text
fits/<dataset>_n<count>_noise<sd>_seed<seed>/
├── data.npz
├── data_hashes.json
├── polynomial/
│   ├── model.json
│   ├── model.before_precision_fix.json
│   ├── predictions.csv
│   └── status.json
├── mlp/
│   ├── model.json
│   ├── learning_curve.csv
│   ├── predictions.csv
│   └── status.json
└── pysr/                     # Present in quick and smoke_all
    ├── model.json
    ├── predictions.csv
    ├── status.json
    └── search/
        ├── candidates.csv
        └── <upstream run>/hall_of_fame.csv + backup CSV
```

The [complete file inventory](../results/artifact_inventory.csv) lists every
packaged source/evidence file, its size and SHA256. Local .venv/, .julia/, runs/,
caches and binary checkpoints are excluded from the deliverable archive.
