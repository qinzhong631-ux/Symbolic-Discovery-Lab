"""Run from repository root; first import can download and compile Julia."""

import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from symbolic_discovery.data import generate
from symbolic_discovery.models.symbolic import SymbolicModel


def main():
    output = Path("results/backend_check")
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    result = {"status": "started", "python": sys.version}
    try:
        import pysr
        from pysr import jl

        result.update(pysr=pysr.__version__, julia=str(jl.seval("VERSION")))
        d = generate("A", n_train=32, n_validation=16, n_test=16, n_ood=16)
        model = SymbolicModel(
            {"niterations": 5, "populations": 3, "timeout_in_seconds": 15, "maxsize": 16},
            42,
            output,
        )
        model.fit(d.train.X, d.train.y, d.validation.X, d.validation.y)
        result.update(
            status="ok", expression=model.expression, training_seconds=model.training_seconds
        )
    except Exception as exc:
        result.update(
            status="failed", error=f"{type(exc).__name__}: {exc}", traceback=traceback.format_exc()
        )
    result["wall_seconds"] = time.perf_counter() - started
    (output / "status.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
