"""Exercise a real local Gradio HTTP/API request and close the server."""

import argparse
import json
from pathlib import Path

from gradio_client import Client

from symbolic_discovery.demo import build_app
from symbolic_discovery.runtime import write_json


def main(include_symbolic=False):
    app = build_app()
    try:
        app.queue(default_concurrency_limit=1).launch(
            server_name="127.0.0.1",
            server_port=7861,
            share=False,
            prevent_thread_lock=True,
            quiet=True,
        )
        client = Client("http://127.0.0.1:7861", verbose=False)
        result = client.predict("A", 0.0, "polynomial", 32, 42, api_name="/run_experiment")
        assert "Ground truth" in result[0]
        assert result[1]["data"][0][0] == "polynomial"
        assert result[1]["data"][0][2] < 1e-8
        assert Path(result[2]).is_file()
        evidence = {
            "status": "ok",
            "url": "http://127.0.0.1:7861",
            "model": "polynomial",
            "test_rmse": result[1]["data"][0][2],
            "plot_type": "png",
        }
        if include_symbolic:
            sequence = []
            for name in ("mlp", "pysr", "all"):
                response = client.predict("C", 0.0, name, 32, 42, api_name="/run_experiment")
                expected = {name} if name != "all" else {"polynomial", "mlp", "pysr"}
                assert set(row[0] for row in response[1]["data"]) == expected
                assert Path(response[2]).is_file()
                sequence.append(name)
            evidence["verified_model_sequence"] = ["polynomial", *sequence]
        write_json(Path("results/demo_check.json"), evidence)
        print(json.dumps(evidence, indent=2))
    finally:
        app.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-symbolic", action="store_true")
    main(parser.parse_args().include_symbolic)
