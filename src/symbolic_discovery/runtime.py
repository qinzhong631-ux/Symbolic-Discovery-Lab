"""Audit records that do not import Julia as a side effect."""

import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def write_json(path, data):
    """Reject nonstandard NaN/Infinity JSON instead of silently publishing it."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False), encoding="utf-8")


def array_hash(array):
    return hashlib.sha256(array.tobytes()).hexdigest()


def environment():
    versions = {}
    for name in [
        "numpy",
        "pandas",
        "scipy",
        "scikit-learn",
        "torch",
        "sympy",
        "matplotlib",
        "gradio",
        "pysr",
        "juliacall",
        "pytest",
    ]:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "packages": versions,
        "git_commit": commit,
        "julia_environment": {
            k: os.getenv(k)
            for k in ["JULIA_DEPOT_PATH", "PYTHON_JULIACALL_THREADS", "PYTHON_JULIAPKG_EXE"]
        },
    }


def source_hashes():
    root = Path(__file__).parent
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*.py"))
    }


def prepare_symbolic_backend():
    """Initialize Julia before Torch; keep failures explicit for baseline fallback."""
    started = time.perf_counter()
    try:
        import pysr
        from pysr import jl

        status = {"status": "ok", "pysr": pysr.__version__, "julia": str(jl.seval("VERSION"))}
    except Exception as exc:
        status = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
    status["seconds"] = time.perf_counter() - started
    return status
