"""One UI request per process; the benchmark CLI retains its warm runtime."""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt

from .demo import run_demo
from .runtime import write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--response", type=Path, required=True)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    description, frame, fig = run_demo(**request)
    figure = args.response.parent / "prediction.png"
    fig.savefig(figure, dpi=160, bbox_inches="tight")
    plt.close(fig)
    clean_frame = frame.astype(object).where(frame.notna(), None)
    write_json(
        args.response,
        {
            "description": description,
            "metrics": clean_frame.to_dict(orient="split"),
            "figure": str(figure.resolve()),
        },
    )


if __name__ == "__main__":
    main()
