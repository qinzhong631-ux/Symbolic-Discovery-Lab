import matplotlib.pyplot as plt
import pytest

from symbolic_discovery.demo import build_app, run_demo, run_demo_isolated


def test_demo_baseline_returns_truth_expression_metrics_and_plot(tmp_path):
    description, frame, figure = run_demo("A", 0.0, "polynomial", 32, 42, output_root=tmp_path)
    assert "2*x0**2" in description
    assert "polynomial" in set(frame.model)
    assert frame.rmse.max() < 1e-8
    assert len(figure.axes) == 2
    plt.close(figure)


def test_demo_builds_and_rejects_invalid_inputs(tmp_path):
    assert build_app() is not None
    with pytest.raises(ValueError):
        run_demo("D", 0.1, "polynomial", 32, 42, output_root=tmp_path)
    with pytest.raises(ValueError):
        run_demo("A", 0.1, "unknown", 32, 42, output_root=tmp_path)


def test_isolated_demo_returns_png_and_metrics(tmp_path):
    from pathlib import Path

    description, frame, path = run_demo_isolated(
        "A", 0.0, "polynomial", 32, 42, output_root=tmp_path
    )
    assert "Ground truth" in description
    assert frame.rmse.max() < 1e-8
    assert Path(path).exists()


@pytest.mark.parametrize("failure", ["ood", "recovery"])
def test_demo_discards_partial_results_on_late_failure(tmp_path, monkeypatch, failure):
    import numpy as np

    import symbolic_discovery.demo as demo

    if failure == "ood":

        class BrokenModel:
            training_seconds = 0.1
            complexity = None
            expression = None

            def predict(self, X):
                if np.any(np.abs(X) > 2):
                    raise ValueError("simulated OOD pole")
                return np.zeros(len(X))

        monkeypatch.setattr(demo, "fit_model", lambda *args: BrokenModel())
    else:

        def broken_recovery(*args):
            raise OSError("simulated recovery export error")

        monkeypatch.setattr(demo, "formula_recovery", broken_recovery)
    with pytest.raises(RuntimeError, match="All selected models failed"):
        run_demo("A", 0.0, "polynomial", 32, 42, output_root=tmp_path)
