"""Trainable CPU PyTorch baseline with validation early stopping."""

import copy
import time

import numpy as np
import torch
from torch import nn

DEFAULTS = {
    "hidden_sizes": [64, 64],
    "epochs": 600,
    "patience": 60,
    "learning_rate": 0.003,
    "weight_decay": 0.0,
    "min_delta": 1e-8,
    "threads": 1,
}


class MLPModel:
    def __init__(self, config, seed):
        if set(config) - set(DEFAULTS):
            raise ValueError("unsupported MLP config keys")
        self.params = {**DEFAULTS, **config}
        p = self.params
        if any(not isinstance(p[k], int) or p[k] < 1 for k in ("epochs", "patience", "threads")):
            raise ValueError("epochs, patience and threads must be positive integers")
        if not p["hidden_sizes"] or any(not isinstance(w, int) or w < 1 for w in p["hidden_sizes"]):
            raise ValueError("hidden_sizes must contain positive integer widths")
        if p["learning_rate"] <= 0 or p["weight_decay"] < 0 or p["min_delta"] < 0:
            raise ValueError("invalid optimizer/early-stopping controls")
        self.seed = seed
        self.expression = None
        self.complexity = None

    def fit(self, X, y, X_validation, y_validation):
        started = time.perf_counter()
        torch.manual_seed(self.seed)
        torch.set_num_threads(self.params["threads"])
        torch.use_deterministic_algorithms(True)
        self.x_mean, self.x_std = X.mean(axis=0), np.maximum(X.std(axis=0), 1e-8)
        self.y_mean, self.y_std = float(y.mean()), max(float(y.std()), 1e-8)

        def tensor(a):
            return torch.tensor(a, dtype=torch.float32, device="cpu")

        xt = tensor((X - self.x_mean) / self.x_std)
        yt = tensor((y - self.y_mean) / self.y_std).reshape(-1, 1)
        xv = tensor((X_validation - self.x_mean) / self.x_std)
        yv = tensor((y_validation - self.y_mean) / self.y_std).reshape(-1, 1)
        layers, width = [], X.shape[1]
        for hidden in self.params["hidden_sizes"]:
            layers.extend([nn.Linear(width, hidden), nn.Tanh()])
            width = hidden
        self.network = nn.Sequential(*layers, nn.Linear(width, 1))
        optimizer = torch.optim.Adam(
            self.network.parameters(),
            lr=self.params["learning_rate"],
            weight_decay=self.params["weight_decay"],
        )
        loss_fn = nn.MSELoss()
        best, stale, best_epoch, best_state = float("inf"), 0, 0, None
        self.history = []
        for epoch in range(1, self.params["epochs"] + 1):
            self.network.train()
            optimizer.zero_grad()
            loss = loss_fn(self.network(xt), yt)
            if not torch.isfinite(loss):
                raise RuntimeError("nonfinite MLP training loss")
            loss.backward()
            optimizer.step()
            self.network.eval()
            with torch.no_grad():
                val = float(loss_fn(self.network(xv), yv)) * self.y_std**2
                train = float(loss_fn(self.network(xt), yt)) * self.y_std**2
            self.history.append({"epoch": epoch, "train_mse": train, "validation_mse": val})
            if val < best:
                improvement = best - val
                best, best_epoch = val, epoch
                best_state = copy.deepcopy(self.network.state_dict())
                if improvement > self.params["min_delta"]:
                    stale = 0
                else:
                    stale += 1
            else:
                stale += 1
            if stale >= self.params["patience"]:
                break
        if best_state is None:
            raise RuntimeError("MLP produced no finite validation checkpoint")
        self.network.load_state_dict(best_state)
        self.training_seconds = time.perf_counter() - started
        self.details = {
            "parameters": self.params,
            "seed": self.seed,
            "device": "cpu",
            "epochs_run": epoch,
            "best_epoch": best_epoch,
            "best_validation_mse": best,
            "parameter_count": sum(p.numel() for p in self.network.parameters()),
            "x_mean": self.x_mean.tolist(),
            "x_std": self.x_std.tolist(),
            "y_mean": self.y_mean,
            "y_std": self.y_std,
            "timing_scope": "initialization + preprocessing + training + restore",
            "activation": "Tanh",
            "batching": "full batch",
            "dtype": "float32",
            "optimizer": "Adam",
            "optimizer_parameters": optimizer.defaults,
        }
        return self

    def predict(self, X):
        self.network.eval()
        with torch.no_grad():
            x = torch.tensor((X - self.x_mean) / self.x_std, dtype=torch.float32)
            return self.network(x).numpy().ravel().astype(float) * self.y_std + self.y_mean
