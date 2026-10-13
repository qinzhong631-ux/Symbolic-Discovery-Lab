"""Small real experiments with durable evidence and explicit failed-model messages."""

import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import gradio as gr
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .data import NAMES, evaluate_truth, generate, truth_expression
from .experiments import fit_model
from .metrics import formula_recovery, regression_metrics
from .plotting import COLORS, LABELS, style
from .runtime import environment, prepare_symbolic_backend, write_json


def run_demo(dataset, noise, model_name, n_train, seed, output_root=Path("runs/demo")):
    if dataset not in NAMES or model_name not in ["all", "polynomial", "mlp", "pysr"]:
        raise ValueError("invalid dataset or model")
    if not float(n_train).is_integer() or not 16 <= n_train <= 512:
        raise ValueError("training samples must be an integer between 16 and 512")
    if not float(seed).is_integer() or not 0 <= seed <= 2**31 - 1:
        raise ValueError("seed must be an integer between 0 and 2^31-1")
    if not np.isfinite(noise) or not 0 <= noise <= 1:
        raise ValueError("noise must be between 0 and 1")
    n_train, seed, noise = int(n_train), int(seed), float(noise)
    models = ["polynomial", "mlp", "pysr"] if model_name == "all" else [model_name]
    backend_status = prepare_symbolic_backend() if "pysr" in models else None
    data = generate(
        dataset, n_train=n_train, n_validation=64, n_test=128, n_ood=128, noise=noise, seed=seed
    )
    directory = Path(output_root) / uuid4().hex
    directory.mkdir(parents=True)
    config = {
        "polynomial": {"degree": 3},
        "mlp": {"epochs": 300, "patience": 40, "hidden_sizes": [32, 32]},
        "pysr": {"niterations": 30, "populations": 4, "maxsize": 20, "timeout_in_seconds": 10},
    }
    grid = np.column_stack([np.linspace(-4, 4, 401), np.zeros(401)])
    style()
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.7), layout="constrained")
    axes[0].plot(
        grid[:, 0],
        evaluate_truth(dataset, grid),
        color="#333333",
        linestyle="--",
        label="Ground truth",
    )
    axes[0].axvspan(-2, 2, alpha=0.06, color="#3b6d91", label="Training range")
    descriptions = [
        f"### Dataset {dataset}: {NAMES[dataset]}",
        f"Ground truth (evaluation only): `{truth_expression(dataset)}`",
        "",
        f"n={n_train}, noise SD={noise:g}, seed={seed}. "
        "The curve is a two-dimensional function slice at x1=0.",
        "",
    ]
    rows, statuses = [], []
    for name in models:
        model_dir = directory / name
        model_dir.mkdir()
        try:
            if name == "pysr" and backend_status["status"] != "ok":
                raise RuntimeError(backend_status["error"])
            model = fit_model(name, config[name], seed, model_dir, data)
            local_rows, local_descriptions = [], []
            test_prediction = None
            for split in ("test", "ood"):
                s = getattr(data, split)
                pred = model.predict(s.X)
                scores = regression_metrics(s.y, pred)
                local_rows.append(
                    {
                        "model": name,
                        "split": split,
                        **scores,
                        "fit_seconds": model.training_seconds,
                        "PySR_complexity": model.complexity,
                    }
                )
                pd.DataFrame(
                    {
                        "x0": s.X[:, 0],
                        "x1": s.X[:, 1],
                        "observed": s.y,
                        "truth": s.clean,
                        "prediction": pred,
                    }
                ).to_csv(model_dir / f"{split}_predictions.csv", index=False)
                if split == "test":
                    test_prediction = pred
            grid_prediction = model.predict(grid)
            write_json(model_dir / "model.json", model.details)
            if hasattr(model, "history"):
                pd.DataFrame(model.history).to_csv(model_dir / "learning_curve.csv", index=False)
            local_descriptions.append(
                f"**{LABELS[name]}:** `{model.expression or 'Neural network; no symbolic expression'}`"
            )
            if model.expression is not None:
                recovery = formula_recovery(model.expression, truth_expression(dataset))
                local_descriptions.append(
                    f"Symbolic recovery with domain probes: {recovery['symbolic_recovery']}; "
                    f"numerical approximation: {recovery['numerical_equivalent']}."
                )
                write_json(model_dir / "recovery.json", recovery)
            axes[0].plot(grid[:, 0], grid_prediction, color=COLORS[name], label=LABELS[name])
            axes[1].scatter(
                data.test.clean,
                test_prediction,
                s=10,
                color=COLORS[name],
                alpha=0.6,
                label=LABELS[name],
            )
            rows.extend(local_rows)
            descriptions.extend(local_descriptions)
            statuses.append({"model": name, "status": "ok"})
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            descriptions.append(f"**{LABELS[name]} failed:** {message}")
            statuses.append({"model": name, "status": "failed", "error": message})
    write_json(
        directory / "manifest.json",
        {
            "dataset": dataset,
            "noise": noise,
            "n_train": n_train,
            "seed": seed,
            "models": models,
            "parameters": config,
            "environment": environment(),
            "statuses": statuses,
            "backend_initialization": backend_status,
        },
    )
    if not rows:
        plt.close(fig)
        raise RuntimeError("All selected models failed; inspect runs/demo for details")
    frame = pd.DataFrame(rows)
    frame.to_csv(directory / "metrics.csv", index=False)
    axes[0].set(xlabel="x0 (x1 = 0)", ylabel="Prediction", title="Function slice: ID and OOD")
    limits = axes[1].get_xlim()
    axes[1].plot(limits, limits, "--", color="#555555", linewidth=1)
    axes[1].set(xlabel="Latent ground truth", ylabel="Prediction", title="Held-out calibration")
    for ax in axes:
        ax.legend(fontsize=8)
    descriptions.extend(
        [
            "",
            "Metrics compare against observed targets. One seed is a demo, "
            "not a statistical benchmark. Numerical approximation is not a proof. "
            "Select Compare all for an algorithm comparison.",
        ]
    )
    fig.savefig(directory / "prediction.png", dpi=160, bbox_inches="tight")
    return "\n\n".join(descriptions), frame, fig


def build_app():
    with gr.Blocks(title="Symbolic Discovery Lab") as app:
        gr.Markdown(
            "# Symbolic Discovery Lab\n"
            "Discovering mathematical laws from data · Reproducible CPU experiments\n\n"
            "Compare interpretable symbolic search, polynomial regression and a neural "
            "network under the same data split. First PySR use may download/compile Julia."
        )
        with gr.Row():
            with gr.Column(scale=1):
                dataset = gr.Dropdown(
                    choices=[
                        ("A · Polynomial", "A"),
                        ("B · Trigonometric", "B"),
                        ("C · Rational", "C"),
                    ],
                    value="A",
                    label="Dataset",
                )
                noise = gr.Slider(0, 1, value=0, step=0.05, label="Gaussian noise SD")
                model = gr.Dropdown(
                    choices=[
                        ("Polynomial regression", "polynomial"),
                        ("MLP neural network", "mlp"),
                        ("PySR formula discovery", "pysr"),
                        ("Compare all", "all"),
                    ],
                    value="polynomial",
                    label="Model",
                )
                n = gr.Slider(16, 512, value=128, step=16, label="Training samples")
                seed = gr.Number(value=42, precision=0, label="Random seed")
                button = gr.Button("Run experiment", variant="primary")
            with gr.Column(scale=3):
                description = gr.Markdown("Run an experiment to inspect the learned model.")
                figure = gr.Image(label="Predictions", interactive=False)
                metrics = gr.Dataframe(
                    label="Held-out comparison (observed targets)", interactive=False
                )
        button.click(
            run_demo_isolated,
            inputs=[dataset, noise, model, n, seed],
            outputs=[description, metrics, figure],
            api_name="run_experiment",
            concurrency_limit=1,
        )
        gr.Markdown(
            "Research evidence and multi-seed results live in the repository. "
            "Search budgets here are deliberately small; recovery is not guaranteed."
        )
    return app


def run_demo_isolated(dataset, noise, model_name, n_train, seed, output_root=Path("runs/demo")):
    """Keep Julia/Torch DLLs in a fresh worker so model switches cannot reverse order."""
    directory = Path(output_root).resolve() / "requests" / uuid4().hex
    directory.mkdir(parents=True)
    request = directory / "request.json"
    response = directory / "response.json"
    write_json(
        request,
        {
            "dataset": dataset,
            "noise": float(noise),
            "model_name": model_name,
            "n_train": float(n_train),
            "seed": float(seed),
            "output_root": str(Path(output_root).resolve()),
        },
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "symbolic_discovery.demo_worker",
            "--request",
            str(request),
            "--response",
            str(response),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        timeout=3600,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    (directory / "worker.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode != 0 or not response.exists():
        raise RuntimeError("Experiment worker failed; inspect runs/demo/requests for its log")
    payload = json.loads(response.read_text(encoding="utf-8"))
    return payload["description"], pd.DataFrame(**payload["metrics"]), payload["figure"]
