"""Independent RNG streams; the oracle is used only here and in evaluation."""

from dataclasses import dataclass

import numpy as np
import sympy as sp

FORMULAS = {"A": "2*x0**2 - 3*x1 + 1", "B": "sin(x0) + x1**2/2", "C": "x0/(1+x1**2)"}
NAMES = {"A": "Polynomial", "B": "Trigonometric", "C": "Rational"}


def truth_expression(dataset: str) -> sp.Expr:
    if dataset not in FORMULAS:
        raise ValueError("dataset must be A, B or C")
    return sp.sympify(FORMULAS[dataset])


def evaluate_truth(dataset: str, X: np.ndarray) -> np.ndarray:
    f = sp.lambdify(sp.symbols("x0 x1"), truth_expression(dataset), "numpy")
    return np.asarray(f(X[:, 0], X[:, 1]), dtype=float)


@dataclass(frozen=True)
class Split:
    X: np.ndarray
    y: np.ndarray
    clean: np.ndarray


@dataclass(frozen=True)
class Dataset:
    train: Split
    validation: Split
    test: Split
    ood: Split
    dataset: str
    seed: int
    noise: float


def generate(
    dataset="A", n_train=256, n_validation=128, n_test=256, n_ood=256, noise=0.0, seed=42
) -> Dataset:
    """ID: [-2,2]^2. OOD: uniform [-4,4]^2 outside the entire ID square.

    Train sizes form nested prefixes; validation/test stay identical across sizes.
    Noise is absolute Gaussian standard deviation on every observed split. Clean
    targets are separately retained for latent-law evaluation, never model input.
    """
    truth_expression(dataset)
    sizes = (n_train, n_validation, n_test, n_ood)
    if any(not isinstance(n, int) or isinstance(n, bool) or n < 2 for n in sizes):
        raise ValueError("split sizes must be integers >= 2")
    if not np.isfinite(noise) or noise < 0:
        raise ValueError("noise must be finite and nonnegative")
    if not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    streams = np.random.SeedSequence(seed).spawn(8)
    splits = []
    for i, n in enumerate(sizes):
        rng = np.random.default_rng(streams[2 * i])
        if i < 3:
            X = rng.uniform(-2, 2, (n, 2))
        else:
            # Fixed draw size makes OOD deterministic independently of requested n.
            chunks, total = [], 0
            while total < n:
                points = rng.uniform(-4, 4, (1024, 2))
                points = points[np.any(np.abs(points) > 2, axis=1)]
                chunks.append(points)
                total += len(points)
            X = np.concatenate(chunks)[:n]
        clean = evaluate_truth(dataset, X)
        y = clean + noise * np.random.default_rng(streams[2 * i + 1]).normal(size=n)
        for array in (X, y, clean):
            array.setflags(write=False)
        splits.append(Split(X, y, clean))
    return Dataset(*splits, dataset, seed, noise)
