"""Generate a factual Markdown report without claiming universal rankings."""

import json
import shutil
from pathlib import Path

import pandas as pd

from .data import truth_expression
from .metrics import formula_recovery
from .runtime import source_hashes, write_json


def table(columns, rows):
    return "\n".join(
        [
            "| " + " | ".join(columns) + " |",
            "| " + " | ".join("---" for _ in columns) + " |",
            *["| " + " | ".join(map(str, row)) + " |" for row in rows],
        ]
    )


def write_report(output, manifest=None):
    output = Path(output)
    if manifest is None:
        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    cfg = manifest["config"]
    lines = [
        "# Recorded experiment report",
        "",
        f"Status: **{manifest['status']}**. Successful fits: "
        f"{len(manifest['fits']) - manifest['failed_fits']}/{manifest['expected_fits']}.",
        "",
        f"Paired seeds: `{cfg['seeds']}`; train sizes: `{cfg['sample_sizes']}`; "
        f"absolute noise SD: `{cfg['noise_levels']}`. Reference n={cfg['reference_n']}.",
        "",
        "All values below are read from saved CSV/JSON files. Sample SD uses ddof=1; "
        "a single seed has no SD. Failures do not enter metric means.",
        "",
        "## Protocol",
        "",
        "ID inputs are uniform on [-2,2]². OOD inputs are uniform on the part of "
        "[-4,4]² outside that square. Independent streams generate each split. "
        "Train sizes are nested prefixes; held-out sets stay fixed. Observed targets "
        "include independent Gaussian noise; clean targets evaluate the latent law.",
        "",
        "Polynomial degree is fixed before evaluation. Feature and target scaling use "
        "training data only. MLP restores its best validation checkpoint. PySR searches "
        "training data with one common operator grammar across datasets; validation "
        "RMSE selects its candidate. True formulas are never search inputs.",
        "",
        "## Reference-condition results",
        "",
    ]
    if (output / "metrics.csv").exists():
        summary = pd.read_csv(output / "summary.csv")
        ref = summary[
            (summary.n_train == cfg["reference_n"])
            & (summary.noise == 0)
            & (summary.target == "clean")
        ]
        rows = []
        for _, r in ref.iterrows():
            std = "n/a" if pd.isna(r.rmse_std) else f"{r.rmse_std:.4g}"
            rows.append(
                [
                    r.dataset,
                    r.model,
                    r.split,
                    int(r.n_seeds),
                    f"{r.rmse_mean:.4g} ± {std}",
                    f"{r.mae_mean:.4g}",
                    f"{r.r2_mean:.4g}",
                    f"{r.training_seconds_mean:.3g}",
                ]
            )
        lines.append(
            table(
                [
                    "Dataset",
                    "Model",
                    "Split",
                    "Seeds",
                    "RMSE mean ± SD",
                    "MAE mean",
                    "R² mean",
                    "Fit seconds mean",
                ],
                rows,
            )
        )
    else:
        lines.append("No successful fits; no metric results are available.")
    lines.extend(
        [
            "",
            "## Formula recovery",
            "",
            "Symbolic recovery requires SymPy to simplify the unrounded expression "
            "difference to exactly zero AND finite unsimplified evaluation on the probes. "
            "Algebraic equality alone can conceal removable domain holes; it is saved "
            "separately as symbolic_equivalent. Failure to prove zero is recorded as not "
            "proven, not mathematical inequivalence. Numerical recovery uses 1,030 "
            "independent ID/OOD/special-point probes, atol=rtol=1e-5; it is finite "
            "evidence of approximation and is **not** symbolic equivalence.",
            "",
        ]
    )
    if (output / "formula_recovery.csv").exists():
        recovery = pd.read_csv(output / "formula_recovery.csv")
        ref = recovery[(recovery.n_train == cfg["reference_n"]) & (recovery.noise == 0)]
        rows = []
        for (dataset, model), group in ref.groupby(["dataset", "model"]):
            rows.append(
                [
                    dataset,
                    model,
                    len(group),
                    f"{group.symbolic_recovery.mean():.1%}",
                    f"{group.numerical_equivalent.mean():.1%}",
                ]
            )
        lines.append(
            table(
                [
                    "Dataset",
                    "Model",
                    "Successful expressions",
                    "Symbolic + domain rate",
                    "Numerical rate",
                ],
                rows,
            )
        )
        grouped = recovery.groupby(["dataset", "n_train", "noise", "model"])
        recovery_summary = grouped[
            ["symbolic_equivalent", "symbolic_recovery", "numerical_equivalent", "finite_on_probes"]
        ].agg(["mean", "std"])
        recovery_summary.columns = ["_".join(c) for c in recovery_summary.columns]
        recovery_summary["n_seeds"] = grouped.seed.nunique()
        recovery_summary.reset_index().to_csv(output / "formula_recovery_summary.csv", index=False)
        lines.extend(["", "### Selected expressions (first recorded seed)", ""])
        for _, r in ref[ref.seed == cfg["seeds"][0]].iterrows():
            lines.append(
                f"- {r.dataset} / {r.model}: `{r.expression}` "
                f"(PySR complexity: {r.expression_complexity}; SymPy nodes: {r.sympy_nodes})"
            )
    lines.extend(["", "## Figures", ""])
    for name in [
        "truth_prediction",
        "noise_robustness",
        "data_efficiency",
        "id_ood",
        "pareto_frontier",
    ]:
        lines.append(f"![{name}](figures/{name}.png)")
    lines.extend(
        [
            "",
            "## Limitations and evidence boundaries",
            "",
            "- These are synthetic two-variable laws, not a real-data benchmark.",
            "- Search is budget limited and stochastic. No algorithm is assumed superior.",
            "- Seed SD is not a confidence interval or a significance test.",
            "- Time budgets, epoch budgets and degree constraints are not compute matched.",
            "- PySR timing includes first-use initialization/JIT where incurred; other "
            "fits reuse the process. Per-fit timing scopes are saved in model.json.",
            "- Wall-clock stopping can change search trajectories even in serial mode.",
            "- PySR tree complexity, SymPy node count and MLP parameter count differ.",
            "- Finite numeric probes cannot prove equality of full mathematical domains.",
            "- Saved CSVs preserve measured predictions. Reruns reproduce the protocol; "
            "wall-clock search limits and hardware can change selected equations.",
            "",
            "## Failed fits",
            "",
        ]
    )
    failures = [f for f in manifest["fits"] if f["status"] != "ok"]
    lines.extend(
        [
            f"- {f['dataset']} / {f['model']} / seed {f['seed']} / "
            f"n={f['n_train']} / noise={f['noise']}: `{f['error']}`"
            for f in failures
        ]
        or ["None."]
    )
    lines.extend(
        [
            "",
            "## Reproduction",
            "",
            "The complete config, environment versions, source SHA256 hashes, data "
            "SHA256 hashes and per-fit parameters are in manifest.json and fits/. "
            "metrics.csv is the raw metric source; summary.csv contains group means/SD. "
            "Regenerate figures with `python -m symbolic_discovery plot --results PATH`.",
        ]
    )
    (output / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def reevaluate_recovery(output):
    """Recompute evaluation from preserved unrounded expressions; never refit/select."""
    output = Path(output)
    path = output / "formula_recovery.csv"
    if path.exists():
        original = output / "formula_recovery.initial.csv"
        if not original.exists():
            shutil.copyfile(path, original)
        frame = pd.read_csv(path)
        records = []
        for _, row in frame.iterrows():
            records.append(
                {**row.to_dict(), **formula_recovery(row.expression, truth_expression(row.dataset))}
            )
        pd.DataFrame(records).to_csv(path, index=False)
    write_json(
        output / "evaluation_revision.json",
        {
            "method": "unsimplified arithmetic probes preserve removable domain holes",
            "source_hashes": source_hashes(),
            "refitted_models": False,
            "prediction_metrics_changed": False,
            "original_recovery_file": "formula_recovery.initial.csv" if path.exists() else None,
        },
    )
    from .plotting import plot_results

    plot_results(output)
    write_report(output)
