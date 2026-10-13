import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Symbolic Discovery Lab")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run all four experiments with paired seeds")
    run.add_argument("--config", type=Path, default=Path("configs/quick.json"))
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--models", nargs="+", choices=["pysr", "polynomial", "mlp"])
    plot = sub.add_parser("plot", help="regenerate figures and report from saved evidence")
    plot.add_argument("--results", type=Path, required=True)
    reevaluate = sub.add_parser("reevaluate", help="recheck saved formulas without refitting")
    reevaluate.add_argument("--results", type=Path, required=True)
    sub.add_parser("demo", help="launch local Gradio demo")
    args = parser.parse_args()
    if args.command == "run":
        from .experiments import run_suite

        config = json.loads(args.config.read_text(encoding="utf-8"))
        if args.models:
            config["models"] = args.models
        manifest = run_suite(config, args.output)
        print(
            f"{manifest['status']}: {len(manifest['fits'])} fits; "
            f"{manifest['failed_fits']} failed. Evidence: {args.output.resolve()}"
        )
        return 0 if manifest["failed_fits"] == 0 else 1
    if args.command == "plot":
        from .plotting import plot_results
        from .report import write_report

        plot_results(args.results)
        write_report(args.results)
        return 0
    if args.command == "reevaluate":
        from .report import reevaluate_recovery

        reevaluate_recovery(args.results)
        return 0
    from .demo import build_app

    build_app().queue(default_concurrency_limit=1).launch(server_name="127.0.0.1", share=False)
    return 0
