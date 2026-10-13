import numpy as np
import pytest

from symbolic_discovery.data import evaluate_truth, generate, truth_expression
from symbolic_discovery.metrics import formula_recovery, regression_metrics


@pytest.mark.parametrize("dataset", ["A", "B", "C"])
def test_seeded_independent_splits(dataset):
    a = generate(dataset, n_train=30, seed=7, noise=0.2)
    b = generate(dataset, n_train=60, seed=7, noise=0.2)
    np.testing.assert_array_equal(a.train.X, b.train.X[:30])
    np.testing.assert_array_equal(a.train.y, b.train.y[:30])
    np.testing.assert_array_equal(a.test.X, b.test.X)
    np.testing.assert_array_equal(a.validation.y, b.validation.y)
    sets = [set(map(tuple, s.X)) for s in [a.train, a.validation, a.test, a.ood]]
    assert all(not sets[i] & sets[j] for i in range(4) for j in range(i))
    assert np.all(np.any(np.abs(a.ood.X) > 2, axis=1))
    np.testing.assert_allclose(a.test.clean, evaluate_truth(dataset, a.test.X))


def test_noise_does_not_change_features_or_oracle():
    a, b = generate("A", noise=0), generate("A", noise=0.5)
    np.testing.assert_array_equal(a.train.X, b.train.X)
    np.testing.assert_array_equal(a.test.clean, b.test.clean)
    assert not np.array_equal(a.train.y, b.train.y)


@pytest.mark.parametrize("kwargs", [{"noise": -1}, {"n_train": 0}, {"dataset": "D"}])
def test_bad_data_controls(kwargs):
    with pytest.raises(ValueError):
        generate(**kwargs)


def test_metrics_and_nonfinite_predictions():
    assert regression_metrics([1, 2, 3], [1, 2, 3])["rmse"] == 0
    with pytest.raises(ValueError):
        regression_metrics([1, 2], [1, np.inf])


def test_recovery_distinguishes_exact_and_approximate():
    exact = formula_recovery("1 - 3*x1 + 2*x0*x0", truth_expression("A"))
    approx = formula_recovery("1.0000001 - 3*x1 + 2*x0**2", truth_expression("A"))
    wrong = formula_recovery("x0", truth_expression("C"))
    assert exact["symbolic_equivalent"] is True
    assert approx["symbolic_equivalent"] is False
    assert approx["numerical_equivalent"] is True
    assert wrong["numerical_equivalent"] is False


def test_numeric_probe_rejects_singular_candidate():
    r = formula_recovery("1/x0", truth_expression("C"))
    assert not r["numerical_equivalent"]


def test_algebraic_cancellation_does_not_hide_numeric_domain_holes():
    r = formula_recovery("x0*x1/x1", "x0")
    assert r["symbolic_equivalent"]
    assert not r["numerical_equivalent"]
