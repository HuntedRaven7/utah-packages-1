#!/usr/bin/env python3
"""Validate package-factory configuration."""
from pathlib import Path

packages = [
    raw.strip()
    for raw in Path("config/bootstrap-packages.txt").read_text().splitlines()
    if raw.strip() and not raw.lstrip().startswith("#")
]
if not packages:
    raise SystemExit("bootstrap package set is empty")
if len(packages) != len(set(packages)):
    raise SystemExit("bootstrap package set contains duplicates")
if any(" " in package or "/" in package for package in packages):
    raise SystemExit("package names must be source RPM names, one per line")
print(f"validated {len(packages)} source RPMs")
