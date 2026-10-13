import json

import numpy as np
import pandas as pd
import pytest

from symbolic_discovery.data import generate
from symbolic_discovery.experiments import aggregate, run_suite, validate_config
from symbolic_discovery.models.mlp import MLPModel
from symbolic_discovery.models.polynomial import PolynomialModel, polynomial_expression


def test_polynomial_recovers_quadratic_and_scaler_is_train_only():
    d = generate("A", n_train=80)
    m = PolynomialModel({"degree": 2}, 42)
    m.fit(d.train.X, d.train.y, d.validation.X + 100, d.validation.y)
    np.testing.assert_allclose(m.predict(d.test.X), d.test.clean, atol=1e-9)
    expected = m.pipeline["features"].transform(d.train.X).mean(axis=0)
    np.testing.assert_allclose(m.pipeline["scale"].mean_, expected)
    assert m.expression is not None


def test_polynomial_export_preserves_float_coefficient_and_does_not_manufacture_recovery():
    import sympy as sp

    from symbolic_discovery.metrics import formula_recovery

    coefficient = 1.0000000000000002
    expression = polynomial_expression([coefficient], 0.0, [[1, 0]])
    exported = sp.sympify(expression).coeff(sp.Symbol("x0"))
    assert float(exported) == coefficient
    assert not formula_recovery(expression, "x0")["symbolic_equivalent"]


def test_mlp_learns_and_restores_best_epoch():
    d = generate("C", n_train=128, n_validation=64)
    m = MLPModel(
        {"hidden_sizes": [32, 32], "epochs": 120, "patience": 30, "learning_rate": 0.01}, 9
    )
    m.fit(d.train.X, d.train.y, d.validation.X, d.validation.y)
    assert m.history[-1]["train_mse"] < m.history[0]["train_mse"]
    val_mse = np.mean((m.predict(d.validation.X) - d.validation.y) ** 2)
    assert val_mse == pytest.approx(m.details["best_validation_mse"], abs=1e-6)
    assert m.details["epochs_run"] <= 120


def test_aggregation_sample_sd_and_failure_counts():
    rows = pd.DataFrame(
        [
            dict(
                dataset="A",
                n_train=32,
                noise=0.0,
                model="mlp",
                split="test",
                target="observed",
                seed=1,
                rmse=1.0,
                mae=1.0,
                r2=0.0,
                training_seconds=2.0,
            ),
            dict(
                dataset="A",
                n_train=32,
                noise=0.0,
                model="mlp",
                split="test",
                target="observed",
                seed=2,
                rmse=3.0,
                mae=3.0,
                r2=1.0,
                training_seconds=4.0,
            ),
        ]
    )
    s = aggregate(rows)
    assert s.iloc[0].rmse_mean == 2
    assert s.iloc[0].rmse_std == pytest.approx(np.sqrt(2))
    assert s.iloc[0].n_seeds == 2
    assert np.isnan(aggregate(rows.iloc[:1]).iloc[0].rmse_std)


def test_small_suite_writes_real_artifacts_and_refuses_overwrite(tmp_path):
    cfg = dict(
        datasets=["A"],
        seeds=[2],
        sample_sizes=[24],
        noise_levels=[0.0],
        reference_n=24,
        models=["polynomial"],
        n_validation=12,
        n_test=12,
        n_ood=12,
        polynomial={"degree": 2},
        mlp={},
        pysr={},
    )
    output = tmp_path / "suite"
    run_suite(cfg, output)
    rows = pd.read_csv(output / "metrics.csv")
    assert rows.rmse.max() < 1e-8
    assert len(rows) == 4  # observed/clean x test/OOD
    assert json.loads((output / "manifest.json").read_text())["status"] == "complete"
    assert (output / "figures" / "truth_prediction.svg").exists()
    with pytest.raises(FileExistsError):
        run_suite(cfg, output)


def test_config_rejects_duplicate_seeds_and_missing_reference():
    with pytest.raises(ValueError):
        validate_config(
            dict(
                datasets=["A"],
                seeds=[1, 1],
                sample_sizes=[32],
                noise_levels=[0.0],
                reference_n=32,
                models=["polynomial"],
            )
        )


def test_artifact_failure_does_not_claim_complete(tmp_path, monkeypatch):
    import symbolic_discovery.plotting as plotting

    def fail_plot(output):
        raise OSError("simulated full disk during figure export")

    monkeypatch.setattr(plotting, "plot_results", fail_plot)
    cfg = dict(
        datasets=["A"],
        seeds=[2],
        sample_sizes=[24],
        noise_levels=[0.0],
        reference_n=24,
        models=["polynomial"],
        n_validation=12,
        n_test=12,
        n_ood=12,
        polynomial={"degree": 2},
    )
    with pytest.raises(OSError):
        run_suite(cfg, tmp_path / "suite")
    manifest = json.loads((tmp_path / "suite" / "manifest.json").read_text())
    assert manifest["status"] == "failed_artifacts"
    assert manifest["artifact_status"] == "failed"


def test_failed_fit_artifacts_are_not_used_by_plots(tmp_path, monkeypatch):
    import symbolic_discovery.experiments as experiments

    def fail_recovery(*args, **kwargs):
        raise RuntimeError("simulated recovery export failure")

    monkeypatch.setattr(experiments, "formula_recovery", fail_recovery)
    original_read_csv = pd.read_csv

    def guarded_read(path, *args, **kwargs):
        assert "predictions.csv" not in str(path), "failed fit leaked into a figure"
        return original_read_csv(path, *args, **kwargs)

    monkeypatch.setattr(pd, "read_csv", guarded_read)
    cfg = dict(
        datasets=["A"],
        seeds=[2],
        sample_sizes=[24],
        noise_levels=[0.0],
        reference_n=24,
        models=["polynomial"],
        n_validation=12,
        n_test=12,
        n_ood=12,
        polynomial={"degree": 2},
    )
    manifest = run_suite(cfg, tmp_path / "suite")
    assert manifest["status"] == "partial"
    assert manifest["failed_fits"] == 1
