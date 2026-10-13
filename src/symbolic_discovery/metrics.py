"""Predictive metrics and conservative formula-recovery evidence."""

import numpy as np
import sympy as sp
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error


def regression_metrics(y, prediction):
    y, prediction = np.asarray(y), np.asarray(prediction)
    if y.shape != prediction.shape or not np.all(np.isfinite(prediction)):
        raise ValueError("predictions must be finite and match target shape")
    return {
        "rmse": float(root_mean_squared_error(y, prediction)),
        "mae": float(mean_absolute_error(y, prediction)),
        "r2": float(r2_score(y, prediction)),
    }


def expression_nodes(expr):
    """SymPy node count, distinct from PySR's search-tree complexity."""
    return sum(1 for _ in sp.preorder_traversal(sp.sympify(expr)))


def evaluate_expression(expr, X):
    expr = sp.sympify(expr)
    variables = sp.symbols("x0 x1")
    if expr.free_symbols - set(variables):
        raise ValueError("expression has unknown symbols")
    with np.errstate(all="ignore"):
        values = sp.lambdify(variables, expr, "numpy")(X[:, 0], X[:, 1])
    return np.broadcast_to(np.asarray(values, dtype=float), (len(X),)).copy()


def formula_recovery(candidate, truth, seed=982451653, atol=1e-5, rtol=1e-5):
    """No rationalization/rounding of fitted constants to manufacture exactness.

    Exact: SymPy proves simplified difference is zero. Approximate: independent
    ID + OOD probes and special points satisfy tolerances. Finite probes are not
    a proof, and a failed symbolic proof is not a proof of inequivalence.
    """
    # Preserve the exported arithmetic tree for numeric probes: eager parsing
    # would cancel x1/x1 and conceal its hole at x1=0.
    candidate = sp.sympify(candidate, evaluate=False)
    truth = sp.sympify(truth)
    exact = bool(sp.simplify(candidate - truth) == 0)
    rng = np.random.default_rng(seed)
    X = np.vstack(
        [
            rng.uniform(-2, 2, (512, 2)),
            rng.uniform(-4, 4, (512, 2)),
            [[0, 0], [0, 1], [1, 0], [-1, -1], [2, 2], [4, 4]],
        ]
    )
    try:
        a, b = evaluate_expression(candidate, X), evaluate_expression(truth, X)
        finite = bool(np.all(np.isfinite(a)) and np.all(np.isfinite(b)))
        approximate = finite and bool(np.allclose(a, b, atol=atol, rtol=rtol))
        max_error = float(np.max(np.abs(a - b))) if finite else None
    except (ValueError, TypeError, OverflowError):
        approximate, max_error, finite = False, None, False
    return {
        "symbolic_equivalent": exact,
        "numerical_equivalent": approximate,
        "finite_on_probes": finite,
        "symbolic_recovery": exact and finite,
        "probe_max_abs_error": max_error,
        "atol": atol,
        "rtol": rtol,
        "probe_seed": seed,
        "probe_count": len(X),
    }
