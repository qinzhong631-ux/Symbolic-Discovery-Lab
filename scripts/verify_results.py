"""Check saved data hashes, recompute CSV metrics, and verify required artifacts."""

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from symbolic_discovery.experiments import aggregate
from symbolic_discovery.metrics import regression_metrics
from symbolic_discovery.runtime import array_hash, write_json


def verify(output):
    output = Path(output)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] in ("complete", "partial")
    assert len(manifest["fits"]) == manifest["expected_fits"]
    scores = pd.read_csv(output / "metrics.csv", float_precision="round_trip")
    checked_data = set()
    checked_fits = 0
    for fit in manifest["fits"]:
        tag = f"{fit['dataset']}_n{fit['n_train']}_noise{fit['noise']:g}_seed{fit['seed']}"
        directory = output / "fits" / tag
        if tag not in checked_data:
            hashes = json.loads((directory / "data_hashes.json").read_text())
            with np.load(directory / "data.npz", allow_pickle=False) as data:
                assert len(data["train_X"]) == fit["n_train"]
                for key, digest in hashes.items():
                    assert array_hash(data[key]) == digest, f"data hash mismatch: {tag}/{key}"
                assert np.all(np.any(np.abs(data["ood_X"]) > 2, axis=1))
            checked_data.add(tag)
        if fit["status"] != "ok":
            continue
        model_dir = directory / fit["model"]
        assert json.loads((model_dir / "status.json").read_text())["status"] == "ok"
        parameters = json.loads((model_dir / "model.json").read_text())
        assert "parameters" in parameters
        predictions = pd.read_csv(model_dir / "predictions.csv", float_precision="round_trip")
        selected = scores[
            (scores.dataset == fit["dataset"])
            & (scores.n_train == fit["n_train"])
            & (scores.noise == fit["noise"])
            & (scores.seed == fit["seed"])
            & (scores.model == fit["model"])
        ]
        assert len(selected) == 4
        for _, record in selected.iterrows():
            p = predictions[predictions.split == record.split]
            values = regression_metrics(
                p.observed if record.target == "observed" else p.truth, p.prediction
            )
            for key, value in values.items():
                np.testing.assert_allclose(value, record[key], rtol=1e-7, atol=1e-12)
        if fit["model"] == "pysr":
            front = pd.read_csv(model_dir / "search" / "candidates.csv")
            chosen = front[front["index"] == parameters["selected_index"]].iloc[0]
            assert chosen.expression == parameters["expression"]
            assert chosen.validation_rmse == front.validation_rmse.min()
        checked_fits += 1
    actual = pd.read_csv(output / "summary.csv")
    expected = aggregate(scores)
    pd.testing.assert_frame_equal(actual, expected, check_dtype=False, rtol=1e-7, atol=1e-12)
    names = ["truth_prediction", "noise_robustness", "data_efficiency", "id_ood", "pareto_frontier"]
    for name in names:
        with Image.open(output / "figures" / f"{name}.png") as image:
            image.verify()
        svg = ET.parse(output / "figures" / f"{name}.svg")
        assert svg.getroot().tag.endswith("svg")
    assert (output / "REPORT.md").exists()
    evidence = {
        "status": "ok",
        "data_conditions_checked": len(checked_data),
        "successful_fits_checked": checked_fits,
        "metrics_recomputed": len(scores),
        "figure_pairs_checked": len(names),
    }
    write_json(output / "integrity_check.json", evidence)
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path("results/quick"))
    verify(parser.parse_args().results)
