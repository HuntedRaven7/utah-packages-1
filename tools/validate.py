#!/usr/bin/env python3
"""Validate package-factory configuration."""
from pathlib import Path

packages = [
    raw.strip()
    for raw in Path("config/bootstrap-packages.txt").read_text().splitlines()
    if raw.strip() and not raw.lstrip().startswith("#")
]
for path in Path("packages").glob("*/.hummingbird-upstream.json"):
    import json
    data = json.loads(path.read_text())
    required = {"package", "branch", "remote", "commit", "tree", "imported_at"}
    if set(data) != required:
        raise SystemExit(f"invalid upstream provenance: {path}")
    if data["branch"] != "rawhide":
        raise SystemExit(f"only rawhide imports are supported: {path}")
if not packages:
    raise SystemExit("bootstrap package set is empty")
if len(packages) != len(set(packages)):
    raise SystemExit("bootstrap package set contains duplicates")
if any(" " in package or "/" in package for package in packages):
    raise SystemExit("package names must be source RPM names, one per line")
print(f"validated {len(packages)} source RPMs")
