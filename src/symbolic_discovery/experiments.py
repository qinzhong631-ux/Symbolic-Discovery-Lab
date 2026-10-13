"""Paired-seed experiments, durable raw evidence and explicit failure records."""

import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

from .data import evaluate_truth, generate, truth_expression
from .metrics import formula_recovery, regression_metrics
from .models.polynomial import PolynomialModel
from .models.symbolic import SymbolicModel
from .runtime import array_hash, environment, prepare_symbolic_backend, source_hashes, write_json

MODELS = {"polynomial": PolynomialModel, "mlp": None, "pysr": SymbolicModel}
KEYS = ["dataset", "n_train", "noise", "model", "split", "target"]


def validate_config(config):
    required = {"datasets", "seeds", "sample_sizes", "noise_levels", "reference_n", "models"}
    if required - set(config):
        raise ValueError(f"missing config keys: {sorted(required - set(config))}")
    for key in ("datasets", "seeds", "sample_sizes", "noise_levels", "models"):
        values = config[key]
        if not isinstance(values, list) or not values or len(set(values)) != len(values):
            raise ValueError(f"{key} must be a nonempty unique list")
    if set(config["datasets"]) - {"A", "B", "C"} or set(config["models"]) - set(MODELS):
        raise ValueError("unknown dataset or model")
    if any(not isinstance(s, int) or s < 0 for s in config["seeds"]):
        raise ValueError("seeds must be nonnegative integers")
    if config["reference_n"] not in config["sample_sizes"] or 0 not in config["noise_levels"]:
        raise ValueError("reference_n must be in sample_sizes and noise_levels must include 0")
    if any(not isinstance(n, int) or n < 2 for n in config["sample_sizes"]):
        raise ValueError("sample sizes must be integers >= 2")
    if any(not np.isfinite(n) or n < 0 for n in config["noise_levels"]):
        raise ValueError("noise levels must be finite and nonnegative")
    for key in ("n_validation", "n_test", "n_ood"):
        n = config.get(key, 256)
        if not isinstance(n, int) or n < 2:
            raise ValueError(f"{key} must be an integer >= 2")
    return config


def aggregate(rows):
    if rows.empty:
        return pd.DataFrame()
    measures = ["rmse", "mae", "r2", "training_seconds"]
    grouped = rows.groupby(KEYS, dropna=False)
    result = grouped[measures].agg(["mean", "std"])
    result.columns = ["_".join(c) for c in result.columns]
    result["n_seeds"] = grouped.seed.nunique()
    return result.reset_index()


def fit_model(name, config, seed, directory, data):
    cls = MODELS[name]
    if name == "mlp":
        from .models.mlp import MLPModel

        cls = MLPModel
    model = cls(config, seed, directory / "search") if name == "pysr" else cls(config, seed)
    model.fit(data.train.X, data.train.y, data.validation.X, data.validation.y)
    return model


def run_suite(config, output):
    validate_config(config)
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"output is nonempty; use a new directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    conditions = sorted(
        {(n, 0.0) for n in config["sample_sizes"]}
        | {(config["reference_n"], float(s)) for s in config["noise_levels"]}
    )
    manifest = {
        "status": "running",
        "config": config,
        "environment": environment(),
        "source_hashes": source_hashes(),
        "conditions": conditions,
        "expected_fits": len(conditions)
        * len(config["datasets"])
        * len(config["seeds"])
        * len(config["models"]),
        "fits": [],
    }
    write_json(output / "manifest.json", manifest)
    backend_status = None
    if "pysr" in config["models"]:
        print(
            "Initializing Julia before PyTorch (first use may take several minutes)...", flush=True
        )
        backend_status = prepare_symbolic_backend()
        manifest["backend_initialization"] = backend_status
        write_json(output / "manifest.json", manifest)
    rows, formulas = [], []
    for dataset in config["datasets"]:
        for n_train, noise in conditions:
            for seed in config["seeds"]:
                tag = f"{dataset}_n{n_train}_noise{noise:g}_seed{seed}"
                directory = output / "fits" / tag
                directory.mkdir(parents=True)
                data = generate(
                    dataset,
                    n_train=n_train,
                    noise=noise,
                    seed=seed,
                    **{k: config.get(k, 256) for k in ("n_validation", "n_test", "n_ood")},
                )
                arrays, hashes = {}, {}
                for split in ("train", "validation", "test", "ood"):
                    s = getattr(data, split)
                    for key in ("X", "y", "clean"):
                        name = f"{split}_{key}"
                        arrays[name] = getattr(s, key)
                        hashes[name] = array_hash(arrays[name])
                np.savez_compressed(directory / "data.npz", **arrays)
                write_json(directory / "data_hashes.json", hashes)
                for name in config["models"]:
                    model_dir = directory / name
                    model_dir.mkdir()
                    identity = dict(
                        dataset=dataset, n_train=n_train, noise=noise, seed=seed, model=name
                    )
                    status = {**identity, "status": "running"}
                    start = time.perf_counter()
                    print(
                        f"[{len(manifest['fits']) + 1}/{manifest['expected_fits']}] {tag} {name}",
                        flush=True,
                    )
                    try:
                        if name == "pysr" and backend_status["status"] != "ok":
                            raise RuntimeError(backend_status["error"])
                        model = fit_model(name, config.get(name, {}), seed, model_dir, data)
                        local_rows, predictions = [], []
                        for split in ("test", "ood"):
                            s = getattr(data, split)
                            pred = model.predict(s.X)
                            for target in ("observed", "clean"):
                                target_y = s.y if target == "observed" else s.clean
                                local_rows.append(
                                    {
                                        **identity,
                                        "split": split,
                                        "target": target,
                                        **regression_metrics(target_y, pred),
                                        "training_seconds": model.training_seconds,
                                        "expression_complexity": model.complexity,
                                    }
                                )
                            predictions.append(
                                pd.DataFrame(
                                    {
                                        "split": split,
                                        "x0": s.X[:, 0],
                                        "x1": s.X[:, 1],
                                        "truth": s.clean,
                                        "observed": s.y,
                                        "prediction": pred,
                                    }
                                )
                            )
                        grid = np.column_stack([np.linspace(-4, 4, 401), np.zeros(401)])
                        predictions.append(
                            pd.DataFrame(
                                {
                                    "split": "slice_x1_zero",
                                    "x0": grid[:, 0],
                                    "x1": grid[:, 1],
                                    "truth": evaluate_truth(dataset, grid),
                                    "observed": np.nan,
                                    "prediction": model.predict(grid),
                                }
                            )
                        )
                        pd.concat(predictions).to_csv(model_dir / "predictions.csv", index=False)
                        write_json(model_dir / "model.json", model.details)
                        if hasattr(model, "history"):
                            pd.DataFrame(model.history).to_csv(
                                model_dir / "learning_curve.csv", index=False
                            )
                        if model.expression is not None:
                            recovery = formula_recovery(model.expression, truth_expression(dataset))
                            formulas.append(
                                {
                                    **identity,
                                    "expression": model.expression,
                                    "expression_complexity": model.complexity,
                                    "sympy_nodes": model.details["sympy_nodes"],
                                    **recovery,
                                }
                            )
                        rows.extend(local_rows)
                        status.update(status="ok", training_seconds=model.training_seconds)
                    except Exception as exc:
                        status.update(
                            status="failed",
                            error=f"{type(exc).__name__}: {exc}",
                            traceback=traceback.format_exc(),
                        )
                        print(status["error"], flush=True)
                    status["wall_seconds"] = time.perf_counter() - start
                    write_json(model_dir / "status.json", status)
                    manifest["fits"].append(status)
                    write_json(output / "manifest.json", manifest)
                    if rows:
                        pd.DataFrame(rows).to_csv(output / "metrics.csv", index=False)
                    if formulas:
                        pd.DataFrame(formulas).to_csv(output / "formula_recovery.csv", index=False)
    frame = pd.DataFrame(rows)
    summary = aggregate(frame)
    summary.to_csv(output / "summary.csv", index=False)
    failures = sum(f["status"] != "ok" for f in manifest["fits"])
    manifest.update(status="finalizing", failed_fits=failures, artifact_status="generating")
    if "pysr" in config["models"] and any(
        f["status"] == "ok" and f["model"] == "pysr" for f in manifest["fits"]
    ):
        from pysr import jl

        manifest["julia_version"] = str(jl.seval("VERSION"))
        manifest["symbolic_regression_version"] = str(
            jl.seval("string(Base.pkgversion(SymbolicRegression))")
        )
    write_json(output / "manifest.json", manifest)
    from .plotting import plot_results
    from .report import write_report

    try:
        plot_results(output)
        manifest.update(
            status="complete" if not failures else "partial", artifact_status="complete"
        )
        write_report(output, manifest=manifest)
    except Exception as exc:
        manifest.update(
            status="failed_artifacts",
            artifact_status="failed",
            artifact_error=f"{type(exc).__name__}: {exc}",
        )
        write_json(output / "manifest.json", manifest)
        raise
    write_json(output / "manifest.json", manifest)
    return manifest
