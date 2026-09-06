#!/usr/bin/env python3
"""Stage grouping and repository management for multi-stage RPM builds."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.package_inventory import PackageRecord, inventory

# Invariant package build-dependency edges documented in docs/targeting-hummingbird.md
KNOWN_EDGES = (
    ("wayland-protocols", "gtk4"),
    ("gtk4", "libadwaita"),
    ("gtk4", "mutter"),
    ("mutter", "gnome-shell"),
    ("gtk4", "gnome-control-center"),
    ("libadwaita", "gnome-control-center"),
    ("malcontent-bootstrap", "malcontent"),
)


def group_by_stage(records: list[PackageRecord]) -> dict[int, list[PackageRecord]]:
    grouped = defaultdict(list)
    for record in records:
        grouped[record.stage].append(record)
    return dict(sorted(grouped.items()))


def stage_packages(stage: int, root: Path) -> list[str]:
    records = inventory(root)
    grouped = group_by_stage(records)
    return sorted(r.name for r in grouped.get(stage, []))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--stage", type=int, required=True, choices=range(5))

    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    if args.command == "list":
        pkgs = stage_packages(args.stage, root)
        print(json.dumps(pkgs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
