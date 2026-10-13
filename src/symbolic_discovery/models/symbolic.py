"""Thin adapter around the upstream PySR implementation; no search reimplementation."""

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from symbolic_discovery.metrics import expression_nodes, regression_metrics

DEFAULTS = {
    "binary_operators": ["+", "-", "*", "/"],
    "unary_operators": ["sin"],
    "niterations": 100,
    "maxsize": 20,
    "populations": 8,
    "timeout_in_seconds": 30,
    "precision": 64,
    "parallelism": "serial",
    "deterministic": True,
    "progress": False,
    "verbosity": 0,
    "input_stream": "devnull",
    "nested_constraints": {"sin": {"sin": 0}},
}
ALLOWED = set(DEFAULTS) | {
    "max_evals",
    "population_size",
    "ncycles_per_iteration",
    "constraints",
    "parsimony",
    "maxdepth",
}


class SymbolicModel:
    def __init__(self, config, seed, output, backend_cls=None):
        unknown = set(config) - ALLOWED
        if unknown:
            raise ValueError(f"unsupported PySR config keys: {sorted(unknown)}")
        self.params = {
            **DEFAULTS,
            **config,
            "random_state": seed,
            "output_directory": str(Path(output)),
            "model_selection": "accuracy",
        }
        self.backend_cls = backend_cls
        self.output = Path(output)
        self.selected_index = None

    def fit(self, X, y, X_validation, y_validation):
        start = time.perf_counter()
        cls = self.backend_cls
        if cls is None:
            from pysr import PySRRegressor

            cls = PySRRegressor
        self.backend = cls(**self.params)
        # No validation, oracle, templates or guesses enter the search.
        self.backend.fit(X, y, variable_names=["x0", "x1"])
        rows = []
        for i, row in self.backend.equations_.iterrows():
            try:
                rmse = regression_metrics(
                    y_validation, self.backend.predict(X_validation, index=i)
                )["rmse"]
            except (ValueError, TypeError, OverflowError):
                rmse = float("inf")
            rows.append(
                {
                    "index": int(i),
                    "complexity": int(row["complexity"]),
                    "train_mse": float(row["loss"]),
                    "validation_rmse": rmse,
                    "expression": str(self.backend.sympy(index=i)),
                }
            )
        if not rows or not any(np.isfinite(r["validation_rmse"]) for r in rows):
            raise RuntimeError("PySR produced no finite validation candidates")
        # Simpler candidates break exact validation ties; test data is never consulted.
        best = min(rows, key=lambda r: (r["validation_rmse"], r["complexity"]))
        self.selected_index = best["index"]
        self.expression = best["expression"]
        self.complexity = best["complexity"]
        self.output.mkdir(parents=True, exist_ok=True)
        self.front = pd.DataFrame(rows)
        self.front.to_csv(self.output / "candidates.csv", index=False)
        self.training_seconds = time.perf_counter() - start
        self.details = {
            "parameters": self.params,
            "selected_index": self.selected_index,
            "expression": self.expression,
            "complexity": self.complexity,
            "sympy_nodes": expression_nodes(self.expression),
            "timing_scope": "import + search + validation selection",
        }
        if hasattr(self.backend, "get_params"):
            # Upstream defaults are version dependent; preserve effective parameters.
            self.details["upstream_parameters"] = json.loads(
                json.dumps(self.backend.get_params(deep=False), default=str)
            )
        return self

    def predict(self, X):
        if self.selected_index is None:
            raise RuntimeError("fit must be called before predict")
        return np.asarray(self.backend.predict(X, index=self.selected_index), dtype=float)
