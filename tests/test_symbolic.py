import os

import numpy as np
import pandas as pd
import pytest

from symbolic_discovery.models.symbolic import SymbolicModel


class FakeBackend:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.equations_ = pd.DataFrame(
            {"complexity": [1, 3], "loss": [0.0, 1.0], "sympy_format": ["0", "x0"]}
        )

    def fit(self, X, y, **kwargs):
        self.train_X = X.copy()

    def predict(self, X, index=None):
        return np.zeros(len(X)) if index == 0 else X[:, 0]

    def sympy(self, index=None):
        return self.equations_.iloc[index].sympy_format


def test_validation_selects_without_oracle_or_test(tmp_path):
    X = np.array([[1.0, 0.0], [2.0, 0.0]])
    model = SymbolicModel({}, seed=4, output=tmp_path, backend_cls=FakeBackend)
    model.fit(X, np.zeros(2), X, X[:, 0])
    assert model.selected_index == 1  # best validation, despite worse training loss
    np.testing.assert_array_equal(model.predict(X), X[:, 0])
    assert model.backend.kwargs["parallelism"] == "serial"
    assert model.backend.kwargs["deterministic"] is True
    assert "guesses" not in model.backend.kwargs


@pytest.mark.pysr
@pytest.mark.skipif(os.getenv("RUN_PYSR_TESTS") != "1", reason="opt-in Julia integration")
def test_real_backend(tmp_path):
    rng = np.random.default_rng(2)
    X = rng.uniform(-1, 1, (32, 2))
    y = X[:, 0] + X[:, 1]
    model = SymbolicModel(
        {"niterations": 5, "populations": 3, "maxsize": 12, "timeout_in_seconds": 20},
        seed=2,
        output=tmp_path,
    )
    model.fit(X, y, X[:8], y[:8])
    assert np.all(np.isfinite(model.predict(X)))
    assert model.expression is not None
