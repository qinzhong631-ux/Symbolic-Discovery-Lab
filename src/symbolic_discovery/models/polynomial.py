"""Fixed-degree polynomial least-squares baseline with train-only preprocessing."""

import time

import numpy as np
import sympy as sp
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from symbolic_discovery.metrics import expression_nodes


def polynomial_expression(coefficients, intercept, powers):
    """Export binary64 coefficients with 17 decimal digits for round-trip safety."""
    x0, x1 = sp.symbols("x0 x1")
    expression = sp.Float(repr(float(intercept)), 17)
    for coefficient, exponents in zip(coefficients, powers, strict=True):
        expression += (
            sp.Float(repr(float(coefficient)), 17)
            * x0 ** int(exponents[0])
            * x1 ** int(exponents[1])
        )
    return str(expression)


class PolynomialModel:
    def __init__(self, config, seed):
        self.params = {"degree": 3, **config}
        if set(self.params) != {"degree"}:
            raise ValueError("polynomial supports only degree")
        if not isinstance(self.params["degree"], int) or not 1 <= self.params["degree"] <= 8:
            raise ValueError("polynomial degree must be an integer from 1 to 8")
        self.pipeline = Pipeline(
            [
                ("features", PolynomialFeatures(self.params["degree"], include_bias=False)),
                ("scale", StandardScaler()),
                ("regression", LinearRegression()),
            ]
        )

    def fit(self, X, y, X_validation, y_validation):
        start = time.perf_counter()
        self.pipeline.fit(X, y)
        features, scaler, reg = (
            self.pipeline[name] for name in ("features", "scale", "regression")
        )
        # Undo feature scaling for an expression in the original coordinates.
        coefficients = reg.coef_ / scaler.scale_
        intercept = reg.intercept_ - np.dot(coefficients, scaler.mean_)
        self.expression = polynomial_expression(coefficients, intercept, features.powers_)
        self.complexity = None  # PySR tree complexity is not defined for this model.
        self.training_seconds = time.perf_counter() - start
        self.details = {
            "parameters": self.params,
            "expression": self.expression,
            "sympy_nodes": expression_nodes(self.expression),
            "coefficient_count": len(coefficients) + 1,
            "timing_scope": "preprocessing + least squares + expression export",
            "estimator_parameters": reg.get_params(),
            "feature_parameters": features.get_params(),
            "raw_coefficients": coefficients.tolist(),
            "raw_intercept": float(intercept),
            "powers": features.powers_.tolist(),
            "export_decimal_digits": 17,
        }
        return self

    def predict(self, X):
        return self.pipeline.predict(X)
