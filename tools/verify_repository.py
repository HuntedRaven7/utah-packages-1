#!/usr/bin/env python3
"""Verify final composed package repository against complete factory inventory."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def _rpm_name(path: Path) -> str:
    try:
        proc = subprocess.run(
            ["rpm", "-qp", "--qf", "%{NAME}", str(path)],
            capture_output=True,
            text=True,
            check=True,
        )
        return proc.stdout.strip()
    except Exception:
        # Fallback to prefix before version
        return path.name.split("-")[0]


def verify_repository(
    repo_dir: Path,
    expected_packages: list[str],
    rpm_names: list[str] | None = None,
) -> bool:
    repomd = repo_dir / "repodata" / "repomd.xml"
    if not repomd.is_file():
        raise ValueError(f"missing repodata in {repo_dir}")

    found_rpms = sorted(repo_dir.glob("**/*.rpm")) if rpm_names is None else [repo_dir / name for name in rpm_names]
    if not found_rpms:
        raise ValueError(f"no RPMs found in {repo_dir}")

    names_found = set()
    for rpm_file in found_rpms:
        if rpm_file.name.endswith(".src.rpm"):
            continue
        names_found.add(_rpm_name(rpm_file))

    missing = [pkg for pkg in expected_packages if pkg not in names_found]
    if missing:
        raise ValueError(f"missing package: {', '.join(sorted(missing))}")

    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo_dir", type=Path)
    parser.add_argument("--expected", type=Path, required=True)
    args = parser.parse_args()

    import json
    data = json.loads(args.expected.read_text())
    expected = data if isinstance(data, list) else [p["name"] for p in data.get("packages", [])]
    verify_repository(args.repo_dir, expected)
    print("repository verified successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
