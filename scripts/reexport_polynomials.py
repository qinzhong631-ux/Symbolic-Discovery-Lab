"""Repair polynomial exports from saved training data, preserving measured metrics."""

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from symbolic_discovery.models.polynomial import PolynomialModel
from symbolic_discovery.report import reevaluate_recovery
from symbolic_discovery.runtime import source_hashes, write_json


def repair(output):
    output = Path(output)
    manifest = json.loads((output / "manifest.json").read_text())
    recovery_path = output / "formula_recovery.csv"
    recovery = pd.read_csv(recovery_path)
    backup = output / "formula_recovery.before_precision_fix.csv"
    if not backup.exists():
        shutil.copyfile(recovery_path, backup)
    records = []
    for fit in manifest["fits"]:
        if fit["model"] != "polynomial" or fit["status"] != "ok":
            continue
        tag = f"{fit['dataset']}_n{fit['n_train']}_noise{fit['noise']:g}_seed{fit['seed']}"
        directory = output / "fits" / tag
        model_dir = directory / "polynomial"
        metadata_path = model_dir / "model.json"
        metadata = json.loads(metadata_path.read_text())
        with np.load(directory / "data.npz") as data:
            model = PolynomialModel(metadata["parameters"], fit["seed"])
            model.fit(data["train_X"], data["train_y"], data["validation_X"], data["validation_y"])
            stored = pd.read_csv(model_dir / "predictions.csv", float_precision="round_trip")
            p = stored[stored.split == "test"]
            prediction = model.predict(data["test_X"])
            np.testing.assert_allclose(prediction, p.prediction, rtol=1e-12, atol=1e-12)
            max_delta = float(np.max(np.abs(prediction - p.prediction)))
        original = model_dir / "model.before_precision_fix.json"
        if not original.exists():
            shutil.copyfile(metadata_path, original)
        for key in (
            "expression",
            "sympy_nodes",
            "raw_coefficients",
            "raw_intercept",
            "powers",
            "export_decimal_digits",
        ):
            metadata[key] = model.details[key]
        metadata["export_reconstruction"] = "deterministic OLS from original saved training arrays"
        write_json(metadata_path, metadata)
        mask = (
            (recovery.dataset == fit["dataset"])
            & (recovery.n_train == fit["n_train"])
            & (recovery.noise == fit["noise"])
            & (recovery.seed == fit["seed"])
            & (recovery.model == "polynomial")
        )
        recovery.loc[mask, "expression"] = model.expression
        recovery.loc[mask, "sympy_nodes"] = model.details["sympy_nodes"]
        records.append({"condition": tag, "max_prediction_delta": max_delta})
    recovery.to_csv(recovery_path, index=False)
    write_json(
        output / "polynomial_export_revision.json",
        {
            "method": "17-digit round-trip coefficients; deterministic OLS reconstruction",
            "refitted_for_export_only": "polynomial",
            "pysr_mlp_refitted": False,
            "metric_records_changed": 0,
            "source_hashes": source_hashes(),
            "checks": records,
        },
    )
    reevaluate_recovery(output)
    print(f"Reexported {len(records)} polynomial models; preserved all measured metrics.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    repair(parser.parse_args().results)
