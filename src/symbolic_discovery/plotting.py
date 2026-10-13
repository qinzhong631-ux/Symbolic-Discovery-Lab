"""Publication-oriented figures generated exclusively from recorded evidence."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

COLORS = {"pysr": "#3b6d91", "polynomial": "#b77942", "mlp": "#7972a5"}
LABELS = {"pysr": "PySR", "polynomial": "Polynomial", "mlp": "MLP"}


def style():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "svg.fonttype": "none",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
            "axes.grid": True,
            "grid.alpha": 0.15,
        }
    )


def save(fig, directory, name):
    for extension in ("png", "svg"):
        fig.savefig(directory / f"{name}.{extension}", dpi=220, bbox_inches="tight")
    plt.close(fig)


def pareto_mask(complexity, error):
    c, e = np.asarray(complexity), np.asarray(error)
    return np.array(
        [not np.any((c <= c[i]) & (e <= e[i]) & ((c < c[i]) | (e < e[i]))) for i in range(len(c))]
    )


def plot_results(output):
    output = Path(output)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    cfg = manifest["config"]
    directory = output / "figures"
    directory.mkdir(exist_ok=True)
    style()
    rows = (
        pd.read_csv(output / "summary.csv") if (output / "metrics.csv").exists() else pd.DataFrame()
    )
    datasets = cfg["datasets"]
    seed, ref = cfg["seeds"][0], cfg["reference_n"]

    def successful(directory):
        status = directory / "status.json"
        return status.exists() and json.loads(status.read_text(encoding="utf-8"))["status"] == "ok"

    def panels(title):
        fig, axes = plt.subplots(
            1,
            len(datasets),
            figsize=(3.8 * len(datasets), 3.5),
            layout="constrained",
            squeeze=False,
        )
        fig.suptitle(title, fontsize=12)
        for ax, dataset in zip(axes[0], datasets, strict=True):
            ax.set_title(f"Dataset {dataset}")
        return fig, axes[0]

    fig, axes = panels(f"Held-out truth vs prediction | n={ref}, noise=0, seed={seed}")
    for ax, dataset in zip(axes, datasets, strict=True):
        found = False
        for model in cfg["models"]:
            path = (
                output / "fits" / f"{dataset}_n{ref}_noise0_seed{seed}" / model / "predictions.csv"
            )
            if not path.exists() or not successful(path.parent):
                continue
            p = pd.read_csv(path).query("split == 'test'")
            ax.scatter(
                p.truth,
                p.prediction,
                s=9,
                alpha=0.5,
                label=LABELS[model],
                color=COLORS[model],
                edgecolors="none",
            )
            found = True
        if found:
            lim = ax.get_xlim()
            ax.plot(lim, lim, "--", color="#555555", linewidth=1)
            ax.legend(fontsize=8)
        else:
            ax.text(0.5, 0.5, "No successful fits", transform=ax.transAxes, ha="center")
        ax.set_xlabel("Latent ground truth")
        ax.set_ylabel("Prediction")
    save(fig, directory, "truth_prediction")

    for name, x, title in [
        ("noise_robustness", "noise", "Noise robustness"),
        ("data_efficiency", "n_train", "Data efficiency"),
    ]:
        fig, axes = panels(title + " | test RMSE, mean ± sample SD")
        for ax, dataset in zip(axes, datasets, strict=True):
            for model in cfg["models"]:
                if rows.empty:
                    continue
                s = rows[
                    (rows.dataset == dataset)
                    & (rows.model == model)
                    & (rows.split == "test")
                    & (rows.target == "observed")
                ]
                s = s[s.n_train == ref] if x == "noise" else s[s.noise == 0]
                s = s.sort_values(x)
                if s.empty:
                    continue
                ax.errorbar(
                    s[x],
                    np.maximum(s.rmse_mean, 1e-12),
                    yerr=s.rmse_std.fillna(0),
                    marker="o",
                    markersize=4,
                    capsize=3,
                    color=COLORS[model],
                    label=LABELS[model],
                )
            ax.set_yscale("log")
            if x == "n_train":
                ax.set_xscale("log")
                ax.set_xticks(cfg["sample_sizes"], [str(n) for n in cfg["sample_sizes"]])
            ax.set_xlabel("Noise standard deviation" if x == "noise" else "Training samples")
            ax.set_ylabel("Observed test RMSE (log)")
            if ax.get_legend_handles_labels()[0]:
                ax.legend(fontsize=8)
        fig.supxlabel(
            f"Requested seeds: {len(cfg['seeds'])}; SD omitted for n=1. "
            "Plot floor 1e−12; exact counts in summary.csv",
            fontsize=8,
        )
        save(fig, directory, name)

    fig, axes = panels(f"Interpolation vs extrapolation | n={ref}, noise=0")
    for ax, dataset in zip(axes, datasets, strict=True):
        for i, model in enumerate(cfg["models"]):
            if rows.empty:
                continue
            s = rows[
                (rows.dataset == dataset)
                & (rows.model == model)
                & (rows.n_train == ref)
                & (rows.noise == 0)
                & (rows.target == "clean")
            ]
            s = s.set_index("split").reindex(["test", "ood"])
            if s.rmse_mean.isna().all():
                continue
            pos = np.arange(2) + (i - (len(cfg["models"]) - 1) / 2) * 0.22
            ax.errorbar(
                pos,
                np.maximum(s.rmse_mean, 1e-12),
                yerr=s.rmse_std.fillna(0),
                marker="o",
                linestyle="none",
                capsize=3,
                color=COLORS[model],
                label=LABELS[model],
            )
        ax.set_xticks([0, 1], ["ID test", "OOD shell"])
        ax.set_yscale("log")
        ax.set_ylabel("Latent-law RMSE (log)")
        if ax.get_legend_handles_labels()[0]:
            ax.legend(fontsize=8)
    fig.supxlabel("Mean ± sample SD across paired seeds; outside [-2,2]² for OOD", fontsize=8)
    save(fig, directory, "id_ood")

    fig, axes = panels(f"Accuracy–complexity tradeoff | validation, n={ref}, seed={seed}, noise=0")
    for ax, dataset in zip(axes, datasets, strict=True):
        path = (
            output
            / "fits"
            / f"{dataset}_n{ref}_noise0_seed{seed}"
            / "pysr"
            / "search"
            / "candidates.csv"
        )
        if path.exists() and successful(path.parent.parent):
            front = pd.read_csv(path)
            front = front[np.isfinite(front.validation_rmse)]
            ax.scatter(
                front.complexity,
                np.maximum(front.validation_rmse, 1e-12),
                color="#bdcbd5",
                label="All candidates",
            )
            front = front[pareto_mask(front.complexity, front.validation_rmse)]
            front = front.sort_values("complexity")
            ax.plot(
                front.complexity,
                np.maximum(front.validation_rmse, 1e-12),
                "o-",
                color=COLORS["pysr"],
                label="Nondominated",
            )
            ax.legend(fontsize=8)
            ax.set_yscale("log")
        else:
            ax.text(0.5, 0.5, "PySR front unavailable", ha="center", transform=ax.transAxes)
        ax.set_xlabel("PySR expression-tree complexity")
        ax.set_ylabel("Validation RMSE")
    save(fig, directory, "pareto_frontier")
