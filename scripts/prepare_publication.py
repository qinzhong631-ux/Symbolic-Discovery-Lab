"""Verify README links and produce a portable inventory of the staged release."""

import hashlib
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".toml",
    ".json",
    ".csv",
    ".svg",
    ".cff",
    ".yml",
    ".yaml",
    ".ps1",
    ".bak",
}


class LinkCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        self.links.extend(value for key, value in attrs if key in ("href", "src") and value)


def main():
    content = (ROOT / "README.md").read_text(encoding="utf-8")
    parser = LinkCollector()
    parser.feed(content)
    links = parser.links + re.findall(r"\]\(([^)]+)\)", content)
    local = [link for link in links if not link.startswith(("https://", "http://", "#"))]
    missing = [link for link in local if not (ROOT / link.split("#")[0]).exists()]
    if missing:
        raise ValueError(f"missing README assets: {missing}")
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode("utf-8").split("\0")
    rows = []
    normalized = 0
    for name in filter(None, names):
        if name == "results/artifact_inventory.csv":
            continue
        path = ROOT / name
        raw = path.read_bytes()
        if path.suffix in TEXT_SUFFIXES or path.name in {"LICENSE", ".gitignore", ".gitattributes"}:
            updated = raw.replace(b"\r\n", b"\n")
            if updated != raw:
                path.write_bytes(updated)
                normalized += 1
            raw = updated
        rows.append({"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    pd.DataFrame(rows).to_csv(
        ROOT / "results/artifact_inventory.csv", index=False, lineterminator="\n"
    )
    print(
        f"README: {len(local)} local links/assets checked; "
        f"inventory: {len(rows)} files; normalized text line endings: {normalized}."
    )


if __name__ == "__main__":
    main()
