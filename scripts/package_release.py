"""Package source and measured evidence; exclude environments, caches and checkpoints."""

import argparse
import hashlib
import os
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE = {
    ".venv",
    ".julia",
    ".git",
    "runs",
    "build",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
}


def main(archive):
    archive = Path(archive).resolve()
    if archive.exists():
        raise FileExistsError(f"archive exists: {archive}")
    files = []
    inventory = ROOT / "results" / "artifact_inventory.csv"
    for directory, subdirs, names in os.walk(ROOT):
        subdirs[:] = sorted(d for d in subdirs if d not in EXCLUDE and not d.endswith(".egg-info"))
        for name in sorted(names):
            path = Path(directory) / name
            if (
                path == inventory
                or path == archive
                or path.suffix in {".pkl", ".pt", ".pyc", ".log"}
            ):
                continue
            files.append(path)
    rows = [
        {
            "path": p.relative_to(ROOT).as_posix(),
            "bytes": p.stat().st_size,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        }
        for p in files
    ]
    pd.DataFrame(rows).to_csv(inventory, index=False)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for path in [*files, inventory]:
            bundle.write(path, Path(ROOT.name) / path.relative_to(ROOT))
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        assert "symbolic-discovery-lab/README.md" in bundle.namelist()
        assert "symbolic-discovery-lab/src/symbolic_discovery/demo_worker.py" in bundle.namelist()
    print(f"Packaged {len(files) + 1} files; {archive.stat().st_size:,} bytes: {archive}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=ROOT.parent / "symbolic-discovery-lab.zip")
    main(parser.parse_args().archive)
